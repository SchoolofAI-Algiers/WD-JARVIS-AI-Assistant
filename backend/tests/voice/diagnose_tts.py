from __future__ import annotations

import asyncio
import importlib.metadata as md
import os
import platform
import sys
from pathlib import Path
import multiprocessing as mp
import time
from queue import Empty

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent


def _find_backend() -> Path | None:
    """Locate the folder that contains the `app` package, wherever this script was put."""
    candidates = [Path.cwd(), Path.cwd() / "backend", *HERE.parents, *(p / "backend" for p in HERE.parents), HERE]
    for base in candidates:
        if (base / "app" / "voice" / "tts.py").is_file():
            return base
    return None


BACKEND = _find_backend()
if BACKEND is not None:
    sys.path.insert(0, str(BACKEND))
OUT = HERE / "diag_out"
OUT.mkdir(exist_ok=True)

SAMPLES = {
    "en": ("en-GB-RyanNeural", "Good evening. All systems are online."),
    "fr": ("fr-FR-HenriNeural", "Bonsoir. Tous les systèmes sont en ligne."),
    "ar": ("ar-DZ-IsmaelNeural", "مساء الخير. جميع الأنظمة تعمل."),
}


def version(pkg: str) -> str:
    try:
        return md.version(pkg)
    except md.PackageNotFoundError:
        return "NOT INSTALLED"


def section(title: str) -> None:
    print(f"\n=== {title} ===")


async def edge_direct() -> dict[str, bool]:
    results: dict[str, bool] = {}
    try:
        import edge_tts
    except ImportError:
        print("edge-tts is not installed")
        return {k: False for k in SAMPLES}
    for lang, (voice, text) in SAMPLES.items():
        data = bytearray()
        try:
            async def pull():
                async for chunk in edge_tts.Communicate(text, voice).stream():
                    if chunk.get("type") == "audio":
                        data.extend(chunk["data"])

            await asyncio.wait_for(pull(), timeout=15)
            if data:
                (OUT / f"edge_{lang}.mp3").write_bytes(data)
                print(f"[{lang}] {voice}: OK, {len(data)} bytes -> diag_out/edge_{lang}.mp3")
                results[lang] = True
            else:
                print(f"[{lang}] {voice}: FAILED - the service returned no audio")
                results[lang] = False
        except Exception as exc:  # the real reason is what we want to see
            print(f"[{lang}] {voice}: FAILED - {type(exc).__name__}: {exc}")
            results[lang] = False
    return results


def clock_and_proxy() -> None:
    """Edge's auth token is only valid in a ~5 minute window: a wrong PC clock gives HTTP 403."""
    import os
    import urllib.error
    import urllib.request
    from datetime import datetime, timezone
    from email.utils import parsedate_to_datetime

    proxies = {k: v for k, v in os.environ.items() if k.upper() in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY")}
    print(f"proxy environment variables: {proxies or 'none'}")
    try:
        try:
            response = urllib.request.urlopen("https://speech.platform.bing.com/", timeout=10)
            header = response.headers.get("Date")
        except urllib.error.HTTPError as exc:  # a 4xx still carries the server's Date header
            header = exc.headers.get("Date")
        if not header:
            print("could not read the server time")
            return
        server = parsedate_to_datetime(header)
        local = datetime.now(timezone.utc)
        skew = (local - server).total_seconds()
        verdict = "OK" if abs(skew) < 120 else "TOO FAR OFF -> sync your Windows clock (Settings > Time & language > Sync now)"
        print(f"PC clock vs Microsoft server: {skew:+.0f} s   {verdict}")
    except Exception as exc:
        print(f"could not reach speech.platform.bing.com at all - {type(exc).__name__}: {exc}")


def pyttsx3_voices() -> None:
    try:
        import pyttsx3

        engine = pyttsx3.init()
        voices = engine.getProperty("voices")
        print(f"{len(voices)} system voice(s) installed:")
        for v in voices:
            print(f"  - {v.name}  languages={getattr(v, 'languages', '?')}")
        from app.voice.tts import pick_offline_voice

        print("Offline voice the fallback will pick (male preferred):")
        for lang in ("en", "fr", "ar"):
            chosen = pick_offline_voice(voices, lang)
            print(f"  [{lang}] {chosen.name if chosen else 'NONE installed'}")
    except Exception as exc:
        print(f"pyttsx3 unavailable - {type(exc).__name__}: {exc}")


async def full_chain() -> dict[str, str | None]:
    """Run the configured chain for en/fr/ar; return which engine spoke each language (None = failed)."""
    from app.voice.models import VoiceConfig
    from app.voice.tts import build_tts

    config = VoiceConfig.from_env()
    tts = build_tts(config)
    print(f"configured chain: {tts.name}   (VOICE_TTS_PROVIDERS={config.tts_providers})")
    warm = getattr(tts, "warmup", None)
    if callable(warm):  # the backend does this in the background at startup
        await asyncio.to_thread(warm)
    spoken_by: dict[str, str | None] = {}
    for lang, (_voice, text) in SAMPLES.items():
        try:
            speech = await tts.synthesize(text, language=lang, profile=config.profile)
            ext = "mp3" if speech.mime_type == "audio/mpeg" else "wav"
            (OUT / f"chain_{lang}.{ext}").write_bytes(speech.audio)
            spoken_by[lang] = speech.provider
            print(f"[{lang}] spoken by: {speech.provider}  voice={speech.voice}  {speech.mime_type}  "
                  f"{len(speech.audio)} bytes -> diag_out/chain_{lang}.{ext}")
        except Exception as exc:
            spoken_by[lang] = None
            print(f"[{lang}] FAILED - {type(exc).__name__}: {exc}")
    return spoken_by


def run_chain() -> dict[str, str | None]:
    """Like asyncio.run, but never waits for worker threads: a Windows speech engine thread can block that wait."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(full_chain())
    finally:
        loop.close()  # shutdown(wait=False) for the default executor

def _chain_worker(result_queue) -> None:
    """Execute the TTS chain in an isolated process."""
    try:
        result_queue.put(("ok", run_chain()))
    except BaseException as exc:
        result_queue.put((
            "error",
            f"{type(exc).__name__}: {exc}",
        ))


def run_chain_isolated(
    timeout: float = 45.0,
) -> dict[str, str | None]:
    """
    Run the TTS chain in a separate process.

    If a native Windows speech component or thread hangs,
    terminate the worker without blocking the main diagnostic.
    """
    ctx = mp.get_context("spawn")
    result_queue = ctx.Queue()

    worker = ctx.Process(
        target=_chain_worker,
        args=(result_queue,),
        daemon=True,
    )
    worker.start()

    deadline = time.monotonic() + timeout
    message = None

    # Wait for a result, but also detect a worker that exits prematurely.
    while time.monotonic() < deadline:
        try:
            message = result_queue.get(timeout=0.25)
            break
        except Empty:
            if not worker.is_alive():
                break

    # Give the process a moment to exit normally.
    if worker.is_alive():
        worker.join(timeout=1.0)

    # Force-terminate the isolated process if cleanup is stuck.
    if worker.is_alive():
        print(
            "[diag] TTS worker did not exit cleanly; "
            "terminating the isolated process.",
            flush=True,
        )
        worker.terminate()
        worker.join(timeout=3.0)
    else:
        worker.join(timeout=1.0)

    # A result may still be arriving through the multiprocessing queue.
    if message is None:
        try:
            message = result_queue.get(timeout=1.0)
        except Empty:
            pass

    result_queue.close()

    if message is None:
        print(
            f"[diag] TTS chain timed out or exited without a result "
            f"after {timeout:.0f} seconds. "
            f"Worker exit code: {worker.exitcode}",
            flush=True,
        )
        return {lang: None for lang in SAMPLES}

    status, payload = message

    if status != "ok":
        print(f"[diag] TTS worker failed: {payload}", flush=True)
        return {lang: None for lang in SAMPLES}

    return payload

def load_env_file() -> None:
    """The backend reads backend/.env (uvicorn --env-file); do the same so this script sees the same settings."""
    env_file = (BACKEND or Path.cwd()) / ".env"
    if not env_file.is_file():
        return
    try:
        from dotenv import load_dotenv

        load_dotenv(env_file, override=False)
        print(f"(settings read from {env_file})")
    except ImportError:
        print(f"(python-dotenv missing: {env_file} not read; set variables in the shell instead)")


def main() -> None:
    section("1. Environment")
    load_env_file()
    print(f"python {platform.python_version()} on {platform.system()}")
    print(f"edge-tts {version('edge-tts')}   pyttsx3 {version('pyttsx3')}   faster-whisper {version('faster-whisper')}")

    section("2. Is the language fix in your tts.py?")
    if BACKEND is None:
        print("could not find backend/app/voice/tts.py from here: run the script from inside the project folder")
    try:
        from app.voice import tts

        has_fix = hasattr(tts, "_looks_french")
        print(f"language fix present: {'YES' if has_fix else 'NO  <-- copy the new tts.py over backend/app/voice/tts.py'}")
        for text in ("JARVIS received: bonjour comment ça va", "JARVIS received: مرحبا", "JARVIS received: hello"):
            print(f"  detect_language -> {tts.detect_language(text, None)!s:3}  for {text[:40]!r}")
    except Exception as exc:
        print(f"could not import app.voice.tts - {type(exc).__name__}: {exc}")

    section("3. Clock and proxy (common causes of an Edge TTS 403)")
    clock_and_proxy()

    section("3b. Edge TTS called directly (needs internet)")
    edge = asyncio.run(edge_direct())

    section("4. Offline fallback (pyttsx3 / Windows voices)")
    pyttsx3_voices()

    section("5. The project's real chain (what the backend actually uses)")
    spoken_by: dict[str, str | None] = {}
    try:
        spoken_by = run_chain_isolated(timeout=45.0)
    except Exception as exc:
        print(f"chain failed - {type(exc).__name__}: {exc}")

    section("Verdict")
    engines = set(spoken_by.values())
    if spoken_by and None not in engines and engines <= {"piper", "edge-tts"}:
        print("All three languages are spoken by neural voices (" + ", ".join(sorted(e for e in engines if e)) + "). "
              "This is a healthy setup." + ("" if all(edge.values()) else " Edge TTS itself is refused on this network; "
              "Piper is covering for it."))
    elif all(edge.values()):
        print("Edge TTS works for all 3 languages. If replies are still English, the backend is running an old tts.py "
              "or an old process: stop it completely and start it again.")
    else:
        failed = [lang for lang, who in spoken_by.items() if who is None]
        print("Edge TTS is refused here and the chain did not give every language a neural voice"
              + (f" (no audio for: {', '.join(failed)})" if failed else "") + ". Add Piper: "
              "pip install piper-tts, download the voices (see docs/voice.md) and set "
              "VOICE_TTS_PROVIDERS=edge,piper,pyttsx3 in backend/.env. "
              "Edge 403 causes to rule out: clock, VPN/proxy/antivirus, DNS, then try another network.")


if __name__ == "__main__":
    try:
        main()
    finally:
        # Leave immediately: Windows speech-engine threads can otherwise keep the process (and Ctrl+C) stuck.
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(0)
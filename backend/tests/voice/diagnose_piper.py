from __future__ import annotations

import sys
import time
import wave
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
BACKEND = next((p for p in (Path.cwd(), Path.cwd() / "backend", HERE.parent) if (p / "app").is_dir()), HERE.parent)
sys.path.insert(0, str(BACKEND))

SAMPLES = {
    "en": "Good evening, sir. All systems are online.",
    "fr": "Bonsoir, monsieur. Tous les systèmes sont en ligne.",
    "ar": "مساء الخير يا سيدي. جميع الأنظمة تعمل.",
}


def main() -> int:
    print(f"python {sys.version.split()[0]}")
    t = time.perf_counter()
    try:
        import piper  # noqa: F401
        from piper import PiperVoice
    except Exception as exc:
        print(f"FAILED to import piper: {type(exc).__name__}: {exc}")
        print("-> pip install piper-tts")
        return 1
    print(f"import piper (loads onnxruntime): {time.perf_counter() - t:.1f}s")

    from app.voice.tts import PiperTTS

    info = PiperTTS().health()
    print(f"voices folder: {info['voices_dir']}")
    print(f"voice files found: {info['voices'] or 'NONE'}")
    if not info["voices"]:
        print("-> python -m piper.download_voices en_GB-alan-medium fr_FR-tom-medium ar_JO-kareem-medium --download-dir voices")
        return 1

    out = HERE / "diag_out"
    out.mkdir(exist_ok=True)
    for lang, stem in info["voices"].items():
        model = Path(info["voices_dir"]) / f"{stem}.onnx"
        print(f"\n[{lang}] {stem}  ({model.stat().st_size / 1e6:.0f} MB)")
        try:
            t = time.perf_counter()
            voice = PiperVoice.load(model)
            print(f"  load model:   {time.perf_counter() - t:.1f}s")
            t = time.perf_counter()
            target = out / f"piper_{lang}.wav"
            with wave.open(str(target), "wb") as wav_file:
                voice.synthesize_wav(SAMPLES[lang], wav_file)
            print(f"  speak:        {time.perf_counter() - t:.1f}s  -> {target}  ({target.stat().st_size} bytes)")
        except Exception as exc:
            print(f"  FAILED: {type(exc).__name__}: {exc}")
    print("\nThe backend gives each TTS engine VOICE_TTS_PROVIDER_TIMEOUT_S seconds (default 8). Warm-up at startup now")
    print("loads the models once, so only the 'speak' time counts per reply.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
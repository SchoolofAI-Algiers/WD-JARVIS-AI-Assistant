"""Text-to-speech layer"""
from __future__ import annotations

import asyncio
import importlib.util
import io
import logging
import os
import re
import tempfile
import threading
import time
import wave
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Callable, Optional, Sequence

from app.core.language import ENGLISH_WORDS, FRENCH_ACCENTS, FRENCH_WORDS, WORD, looks_french

from .models import SpeechResult, TTSError, VoiceConfig, VoiceErrorCode, VoiceProfile

logger = logging.getLogger("jarvis.voice.tts")


# Text preparation
_CODE_BLOCK = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE = re.compile(r"`([^`]*)`")
_MD_LINK = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")
_URL = re.compile(r"https?://\S+|www\.\S+")
_HEADING = re.compile(r"^#{1,6}\s*")
_BULLET = re.compile(r"^(?:[-*+\u2022]|\d+[.)])\s+")
_BLOCKQUOTE = re.compile(r"^>\s?")
_BOLD = re.compile(r"(\*\*|__)(.+?)\1")
_ITALIC = re.compile(r"\*(\S(?:[^*]*?\S)?)\*")
_RULE_LINE = re.compile(r"[\s|:\-_=*]+")
_EMOJI = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F\u200d]")
_SENTENCE_END = re.compile(r"(?<=[.!?\u2026\u061f])\s+")
_TERMINAL = ".!?\u2026:;\u061f"
_ARABIC_CHAR = re.compile(r"[\u0600-\u06FF]")
_NON_LATIN_LANGS = {"ar"}

# A reply that is mostly Latin text with a short Arabic part (e.g. the placeholder prefix
# "JARVIS received: " + a one-word Arabic message) must still get the Arabic voice: an English or
# French voice cannot read Arabic script at all and produces silence.
_ARABIC_MIN_LETTERS = 3
_ARABIC_MIN_SHARE = 0.15

# French-vs-English heuristics live in app.core.language (shared with the Assistant Core).
_FRENCH_ACCENTS = FRENCH_ACCENTS
_WORD = WORD
_FRENCH_WORDS = FRENCH_WORDS
_ENGLISH_WORDS = ENGLISH_WORDS

_PHRASES = {
    "en": {"more": "The full answer is on your screen.", "code": "The code is on your screen."},
    "fr": {"more": "La réponse complète est affichée à l'écran.", "code": "Le code est affiché à l'écran."},
    "ar": {"more": "الإجابة الكاملة معروضة على الشاشة.", "code": "الشيفرة معروضة على الشاشة."},
}


def _normalise_lines(text: str) -> str:
    out: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or _RULE_LINE.fullmatch(line):
            continue
        structural = bool(_HEADING.match(line) or _BULLET.match(line))
        line = _BLOCKQUOTE.sub("", line, count=1)
        line = _HEADING.sub("", line, count=1)
        line = _BULLET.sub("", line, count=1)
        if "|" in line:  # markdown table row
            line = re.sub(r"\s*\|\s*", ", ", line.strip("| ")).strip(", ")
            structural = True
        if structural and line and line[-1] not in _TERMINAL:
            line += "."
        if line:
            out.append(line)
    return " ".join(out)


def _truncate_to_sentences(text: str, max_chars: int) -> str:
    kept = ""
    for sentence in _SENTENCE_END.split(text):
        candidate = f"{kept} {sentence}".strip()
        if len(candidate) > max_chars:
            break
        kept = candidate
    if kept:
        return kept
    cut = text[:max_chars].rsplit(" ", 1)[0].rstrip(",;:")  # first sentence alone is too long
    return (cut or text[:max_chars]) + "\u2026"


def prepare_spoken_text(text: str, max_chars: int = 600, language: str = "en") -> tuple[str, bool]:
    """Return ``(speakable_text, truncated)`` for a chat reply."""
    if not text or not text.strip():
        return "", False
    phrases = _PHRASES.get(language, _PHRASES["en"])

    had_code = bool(_CODE_BLOCK.search(text))
    cleaned = _CODE_BLOCK.sub(" ", text)
    cleaned = _MD_LINK.sub(r"\1", cleaned)
    cleaned = _URL.sub("", cleaned)
    cleaned = _INLINE_CODE.sub(r"\1", cleaned)
    cleaned = _normalise_lines(cleaned)
    cleaned = _BOLD.sub(r"\2", cleaned)
    cleaned = _ITALIC.sub(r"\1", cleaned)
    cleaned = _EMOJI.sub("", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    truncated = len(cleaned) > max_chars
    if truncated:
        cleaned = _truncate_to_sentences(cleaned, max_chars)
    if truncated:
        cleaned = f"{cleaned} {phrases['more']}"
    elif had_code and cleaned:
        cleaned = f"{cleaned} {phrases['code']}"
    return cleaned, truncated


def detect_language(
    text: str,
    hint: Optional[str] = None,
    default: str = "en",
    supported: Sequence[str] = ("en", "fr", "ar"),
) -> str:
    """Pick the TTS language for a reply.

    Arabic script is detected from the text itself. For Latin-script text we trust the
    STT language hint (so a French question gets a French voice) when a voice exists;
    without a hint (typed messages) French is guessed from the words and accents.
    """
    letters = [c for c in text if c.isalpha()]
    if letters:
        arabic = sum(1 for c in letters if _ARABIC_CHAR.match(c))
        if arabic >= _ARABIC_MIN_LETTERS and arabic / len(letters) >= _ARABIC_MIN_SHARE and "ar" in supported:
            return "ar"
    if hint:
        base = hint.lower().split("-")[0]
        if base in supported and base not in _NON_LATIN_LANGS:
            return base
    if "fr" in supported and _looks_french(text):
        return "fr"
    return default


_looks_french = looks_french  # kept under its old name (verification/diagnose_tts.py checks for it)


def sniff_audio_mime(data: bytes) -> str:
    """Best-effort MIME type from the file header."""
    if data[:4] == b"RIFF" and data[8:12] == b"WAVE":
        return "audio/wav"
    if data[:4] == b"FORM" and data[8:12] in (b"AIFF", b"AIFC"):
        return "audio/aiff"
    if data[:4] == b"OggS":
        return "audio/ogg"
    if data[:3] == b"ID3" or (len(data) > 1 and data[0] == 0xFF and (data[1] & 0xE0) == 0xE0):
        return "audio/mpeg"
    return "application/octet-stream"


# Provider interface
class TTSProvider(ABC):
    name: str = "tts"

    @abstractmethod
    async def synthesize(self, text: str, *, language: str, profile: VoiceProfile) -> SpeechResult:
        """Turn ``text`` into audio. Raises ``TTSError``."""

    def is_available(self) -> bool:
        """Cheap check used by health endpoints (cannot detect network outages)."""
        return True
    
    def health(self) -> dict[str, Any]:
        return {"available": self.is_available()}

# Edge neural voices (online)
class EdgeTTS(TTSProvider):
    name = "edge-tts"

    def __init__(self, *, communicate_factory: Optional[Callable[..., Any]] = None):
        self._factory = communicate_factory

    def is_available(self) -> bool:
        return self._factory is not None or importlib.util.find_spec("edge_tts") is not None

    def _communicate(self, text: str, voice: str, profile: VoiceProfile) -> Any:
        kwargs = {"rate": profile.rate, "pitch": profile.pitch, "volume": profile.volume}
        if self._factory is not None:
            return self._factory(text, voice, **kwargs)
        try:
            import edge_tts
        except ImportError as exc:
            raise TTSError(VoiceErrorCode.TTS_UNAVAILABLE, "edge-tts is not installed") from exc
        return edge_tts.Communicate(text, voice, **kwargs)

    async def synthesize(self, text: str, *, language: str, profile: VoiceProfile) -> SpeechResult:
        voice = profile.voice_for(language)
        communicate = self._communicate(text, voice, profile)
        audio = bytearray()
        try:
            async for chunk in communicate.stream():
                if chunk.get("type") == "audio":
                    audio.extend(chunk["data"])
        except TTSError:
            raise
        except Exception as exc:  # offline, DNS failure, service change, rejected voice name...
            raise TTSError(VoiceErrorCode.TTS_UNAVAILABLE, f"{type(exc).__name__}: {exc}") from exc
        if not audio:
            raise TTSError(VoiceErrorCode.TTS_UNAVAILABLE, "edge-tts returned no audio")
        return SpeechResult(
            audio=bytes(audio), mime_type="audio/mpeg", provider=self.name, voice=voice, spoken_text=text
        )


# Offline system voice
_LANGUAGE_NAMES = {"en": "english", "fr": "french", "ar": "arabic"}
# Windows (SAPI5) voices rarely report a gender, so fall back on well-known first names.
_MALE_VOICE_HINTS = (
    "david", "mark", "george", "james", "richard", "guy", "ryan", "sean", "paul", "claude", "henri",
    "thomas", "antoine", "naayf", "maged", "hamed", "shakir", "ismael",
)
_FEMALE_VOICE_HINTS = (
    "zira", "hazel", "susan", "linda", "heera", "eva", "hortense", "julie", "denise", "hedda", "hoda",
    "salma", "zariyah", "aria", "jenny",
)


def _voice_languages(voice: Any) -> set[str]:
    found: set[str] = set()
    for item in getattr(voice, "languages", None) or []:
        if isinstance(item, bytes):
            item = item.decode("utf-8", "ignore")
        match = re.search(r"[a-zA-Z]{2,3}", str(item))
        if match:
            found.add(match.group(0).lower())
    return found


def _voice_matches_language(voice: Any, language: str) -> bool:
    if language in _voice_languages(voice):
        return True
    return _LANGUAGE_NAMES.get(language, "\0") in str(getattr(voice, "name", "")).lower()


def _male_score(voice: Any) -> int:
    """2 = known male, 1 = unknown, 0 = known female."""
    gender = str(getattr(voice, "gender", "") or "").lower()
    name = str(getattr(voice, "name", "")).lower()
    if gender.startswith("male") or any(hint in name for hint in _MALE_VOICE_HINTS):
        return 2
    if gender.startswith("female") or any(hint in name for hint in _FEMALE_VOICE_HINTS):
        return 0
    return 1


def pick_offline_voice(voices: Sequence[Any], language: str) -> Optional[Any]:
    """Best installed voice for ``language``, preferring a male one (J.A.R.V.I.S. is a man).

    Returns ``None`` when no installed voice speaks ``language``.
    """
    matching = [v for v in voices if _voice_matches_language(v, language)]
    return max(matching, key=_male_score) if matching else None


class Pyttsx3TTS(TTSProvider):
    """Offline fallback using the operating system's voices (SAPI5 / NSSpeech / eSpeak).

    Picks an installed male voice for the requested language. English falls back to any male voice;
    French without a French voice is read by the English male voice (accent will be off). Arabic without
    an Arabic voice raises ``TTSError`` instead of returning silent audio.
    """

    name = "pyttsx3"

    def __init__(self, *, engine_factory: Optional[Callable[[], Any]] = None):
        self._factory = engine_factory
        self._lock = threading.Lock()

    def is_available(self) -> bool:
        return self._factory is not None or importlib.util.find_spec("pyttsx3") is not None

    def _engine(self) -> Any:
        if self._factory is not None:
            return self._factory()
        try:
            import pyttsx3
        except ImportError as exc:
            raise TTSError(VoiceErrorCode.TTS_UNAVAILABLE, "pyttsx3 is not installed") from exc
        try:
            return pyttsx3.init()
        except Exception as exc:  # e.g. eSpeak missing on Linux
            raise TTSError(VoiceErrorCode.TTS_UNAVAILABLE, f"pyttsx3 could not start: {exc}") from exc

    def _select_voice(self, engine: Any, language: str) -> Optional[Any]:
        """Return the voice to use, or ``None`` to keep the engine's default (engines without a voice list)."""
        getter = getattr(engine, "getProperty", None)
        if getter is None:
            return None
        try:
            voices = list(getter("voices") or [])
        except Exception:
            return None
        if not voices:
            return None
        base = (language or "en").lower().split("-")[0]
        voice = pick_offline_voice(voices, base)
        if voice is not None:
            return voice
        if base in _NON_LATIN_LANGS:  # an English voice reads Arabic script as silence
            raise TTSError(
                VoiceErrorCode.TTS_UNAVAILABLE,
                f"no offline '{base}' voice installed (Windows: Settings > Time & language > Speech > Add voices)",
            )
        logger.warning("No offline '%s' voice installed; using an English voice", base)
        return pick_offline_voice(voices, "en") or max(voices, key=_male_score)

    async def synthesize(self, text: str, *, language: str, profile: VoiceProfile) -> SpeechResult:
        return await asyncio.to_thread(self._synthesize_blocking, text, language, profile)

    def _synthesize_blocking(self, text: str, language: str, profile: VoiceProfile) -> SpeechResult:
        with self._lock:  # pyttsx3 engines are not thread-safe
            engine = self._engine()
            voice = self._select_voice(engine, language)
            fd, path = tempfile.mkstemp(suffix=".wav")
            os.close(fd)
            try:
                if voice is not None:
                    engine.setProperty("voice", voice.id)
                engine.setProperty("rate", profile.offline_rate_wpm)
                engine.save_to_file(text, path)
                engine.runAndWait()
                data = Path(path).read_bytes()
            except TTSError:
                raise
            except Exception as exc:
                raise TTSError(VoiceErrorCode.TTS_UNAVAILABLE, f"{type(exc).__name__}: {exc}") from exc
            finally:
                try:
                    os.remove(path)
                except OSError:
                    pass
        if not data:
            raise TTSError(VoiceErrorCode.TTS_UNAVAILABLE, "pyttsx3 produced no audio")
        voice_name = getattr(voice, "name", None) or "system-default"
        return SpeechResult(
            audio=data, mime_type=sniff_audio_mime(data), provider=self.name, voice=voice_name, spoken_text=text
        )


# Google Translate voices (online, no API key)
class GTTS(TTSProvider):
    """Second online option for when Edge TTS is refused (e.g. HTTP 403 from Microsoft's service).

    Opt-in: ``VOICE_TTS_PROVIDERS=edge,gtts,pyttsx3``. Speaks English, French and Arabic with the right
    language, but it is a generic voice: the J.A.R.V.I.S. rate/pitch settings do not apply.
    """

    name = "gtts"
    _LANGUAGES = {"en": ("en", "co.uk"), "fr": ("fr", "fr"), "ar": ("ar", "com")}  # (gTTS language, accent domain)

    def __init__(self, *, speaker_factory: Optional[Callable[..., Any]] = None):
        self._factory = speaker_factory

    def is_available(self) -> bool:
        return self._factory is not None or importlib.util.find_spec("gtts") is not None

    def _speaker(self, text: str, lang: str, tld: str) -> Any:
        if self._factory is not None:
            return self._factory(text, lang, tld)
        try:
            from gtts import gTTS
        except ImportError as exc:
            raise TTSError(VoiceErrorCode.TTS_UNAVAILABLE, "gTTS is not installed (pip install gTTS)") from exc
        return gTTS(text, lang=lang, tld=tld)

    async def synthesize(self, text: str, *, language: str, profile: VoiceProfile) -> SpeechResult:
        return await asyncio.to_thread(self._synthesize_blocking, text, language, profile)

    def _synthesize_blocking(self, text: str, language: str, profile: VoiceProfile) -> SpeechResult:
        base = (language or profile.default_language).lower().split("-")[0]
        lang, tld = self._LANGUAGES.get(base) or self._LANGUAGES[profile.default_language]
        buffer = io.BytesIO()
        try:
            self._speaker(text, lang, tld).write_to_fp(buffer)  # network call
        except TTSError:
            raise
        except Exception as exc:  # offline, blocked, rate-limited, service change...
            raise TTSError(VoiceErrorCode.TTS_UNAVAILABLE, f"{type(exc).__name__}: {exc}") from exc
        data = buffer.getvalue()
        if not data:
            raise TTSError(VoiceErrorCode.TTS_UNAVAILABLE, "gTTS returned no audio")
        return SpeechResult(
            audio=data, mime_type="audio/mpeg", provider=self.name, voice=f"google-{lang}", spoken_text=text
        )


# Piper neural voices (offline, no account, no network)
class PiperTTS(TTSProvider):
    """Offline neural male voices (https://github.com/OHF-Voice/piper1-gpl, voices: rhasspy/piper-voices).

    Needs ``pip install piper-tts`` and the voice files in ``VOICE_PIPER_DIR`` (default ``backend/voices``)::

        python -m piper.download_voices en_GB-alan-medium fr_FR-tom-medium ar_JO-kareem-medium --download-dir voices

    Enable it with ``VOICE_TTS_PROVIDERS=edge,piper,pyttsx3``. A language whose voice file is missing raises
    ``TTSError`` so the chain moves on. Rate/pitch from the voice profile do not apply.
    """

    name = "piper"
    # First existing file wins (model stem, without ``.onnx``).
    _VOICES = {
        "en": ("en_GB-alan-medium", "en_GB-alan-low"),
        "fr": ("fr_FR-tom-medium", "fr_FR-gilles-low"),
        "ar": ("ar_JO-kareem-medium", "ar_JO-kareem-low"),
    }

    def __init__(self, *, voices_dir: Optional[Path] = None, voice_loader: Optional[Callable[[Path], Any]] = None):
        default_dir = Path(os.environ.get("VOICE_PIPER_DIR") or Path(__file__).resolve().parents[2] / "voices")
        self._dir = Path(voices_dir) if voices_dir is not None else default_dir
        self._loader = voice_loader
        self._loaded: dict[Path, Any] = {}
        self._lock = threading.Lock()

    def is_available(self) -> bool:
        return self._loader is not None or importlib.util.find_spec("piper") is not None

    def health(self) -> dict[str, Any]:
        found = {lang: stem for lang in self._VOICES if (stem := self._find_stem(lang))}
        return {"available": self.is_available(), "voices_dir": str(self._dir), "voices": found}

    def _find_stem(self, language: str) -> Optional[str]:
        base = (language or "en").lower().split("-")[0]
        for stem in self._VOICES.get(base, self._VOICES["en"]):
            if (self._dir / f"{stem}.onnx").is_file():
                return stem
        return None

    def _load(self, model: Path) -> Any:
        if model in self._loaded:
            return self._loaded[model]
        if self._loader is not None:
            voice = self._loader(model)
        else:
            try:
                from piper import PiperVoice
            except ImportError as exc:
                raise TTSError(VoiceErrorCode.TTS_UNAVAILABLE, "piper-tts is not installed (pip install piper-tts)") from exc
            voice = PiperVoice.load(model)
        self._loaded[model] = voice
        return voice

    def warmup(self) -> None:
        """Load every available voice model now (importing onnxruntime + reading the model is slow on a cold start)."""
        for language in self._VOICES:
            stem = self._find_stem(language)
            if stem is None:
                continue
            try:
                with self._lock:
                    self._load(self._dir / f"{stem}.onnx")
            except Exception as exc:
                logger.warning("Piper warm-up failed for '%s': %s", language, exc)

    async def synthesize(self, text: str, *, language: str, profile: VoiceProfile) -> SpeechResult:
        return await asyncio.to_thread(self._synthesize_blocking, text, language)

    def _synthesize_blocking(self, text: str, language: str) -> SpeechResult:
        stem = self._find_stem(language)
        if stem is None:
            raise TTSError(
                VoiceErrorCode.TTS_UNAVAILABLE,
                f"no Piper voice file for '{language}' in {self._dir} "
                "(python -m piper.download_voices en_GB-alan-medium fr_FR-tom-medium ar_JO-kareem-medium --download-dir voices)",
            )
        try:
            with self._lock:  # one model at a time keeps memory and CPU predictable
                voice = self._load(self._dir / f"{stem}.onnx")
                buffer = io.BytesIO()
                with wave.open(buffer, "wb") as wav_file:
                    voice.synthesize_wav(text, wav_file)
                data = buffer.getvalue()
        except TTSError:
            raise
        except Exception as exc:
            raise TTSError(VoiceErrorCode.TTS_UNAVAILABLE, f"{type(exc).__name__}: {exc}") from exc
        if len(data) <= 44:  # WAV header only = no samples
            raise TTSError(VoiceErrorCode.TTS_UNAVAILABLE, "piper produced no audio")
        return SpeechResult(audio=data, mime_type="audio/wav", provider=self.name, voice=stem, spoken_text=text)


# Fallback chain + factory
class FallbackTTS(TTSProvider):
    """Try providers in order; remember recent failures (simple circuit breaker)."""

    def __init__(
        self,
        providers: Sequence[TTSProvider],
        *,
        per_provider_timeout_s: float = 8.0,
        cooldown_s: float = 30.0,
        clock: Callable[[], float] = time.monotonic,
    ):
        if not providers:
            raise ValueError("FallbackTTS needs at least one provider")
        self.providers = list(providers)
        self.name = "fallback(" + ">".join(p.name for p in self.providers) + ")"
        self._timeout = per_provider_timeout_s
        self._cooldown = cooldown_s
        self._clock = clock
        self._skip_until: dict[str, float] = {}

    def is_available(self) -> bool:
        return any(p.is_available() for p in self.providers)

    def warmup(self) -> None:
        """Let providers that have something slow to load (Piper models) do it before the first request."""
        for provider in self.providers:
            warm = getattr(provider, "warmup", None)
            if callable(warm):
                try:
                    warm()
                except Exception as exc:
                    logger.warning("TTS warm-up failed for %s: %s", provider.name, exc)

    async def synthesize(self, text: str, *, language: str, profile: VoiceProfile) -> SpeechResult:
        errors: list[str] = []
        last_index = len(self.providers) - 1
        for index, provider in enumerate(self.providers):
            if index < last_index and self._clock() < self._skip_until.get(provider.name, 0.0):
                errors.append(f"{provider.name}: skipped (failed recently)")
                continue  # the last provider is never skipped
            try:
                result = await asyncio.wait_for(
                    provider.synthesize(text, language=language, profile=profile), timeout=self._timeout
                )
                self._skip_until.pop(provider.name, None)
                return result
            except asyncio.TimeoutError:
                errors.append(f"{provider.name}: timed out after {self._timeout:g}s")
            except TTSError as exc:
                errors.append(f"{provider.name}: {exc.detail}")
            except Exception as exc:
                errors.append(f"{provider.name}: {type(exc).__name__}: {exc}")
            self._skip_until[provider.name] = self._clock() + self._cooldown
            logger.warning("TTS provider failed -> %s", errors[-1])
        raise TTSError(VoiceErrorCode.TTS_UNAVAILABLE, "; ".join(errors))


_REGISTRY: dict[str, Callable[[], TTSProvider]] = {"edge": EdgeTTS, "gtts": GTTS, "piper": PiperTTS, "pyttsx3": Pyttsx3TTS}


def build_tts(config: Optional[VoiceConfig] = None) -> TTSProvider:
    """Build the TTS stack from ``config.tts_providers`` (default: edge, then pyttsx3; ``gtts`` is opt-in)."""
    config = config or VoiceConfig()
    providers: list[TTSProvider] = []
    for name in config.tts_providers:
        factory = _REGISTRY.get(name.strip().lower())
        if factory is None:
            raise ValueError(f"Unknown TTS provider '{name}' (known: {', '.join(_REGISTRY)})")
        providers.append(factory())
    if not providers:
        raise ValueError("No TTS provider configured")
    if len(providers) == 1:
        return providers[0]
    return FallbackTTS(providers, per_provider_timeout_s=config.tts_provider_timeout_s)
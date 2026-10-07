"""Text-to-speech layer"""
from __future__ import annotations

import asyncio
import importlib.util
import logging
import os
import re
import tempfile
import threading
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Callable, Optional, Sequence

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
    STT language hint (so a French question gets a French voice) when a voice exists.
    """
    letters = [c for c in text if c.isalpha()]
    if letters:
        arabic = sum(1 for c in letters if _ARABIC_CHAR.match(c))
        if arabic / len(letters) > 0.3 and "ar" in supported:
            return "ar"
    if hint:
        base = hint.lower().split("-")[0]
        if base in supported and base not in _NON_LATIN_LANGS:
            return base
    return default


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
class Pyttsx3TTS(TTSProvider):
    """Offline fallback using the operating system's voices (SAPI5 / NSSpeech / eSpeak), uses the system default voice"""
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

    async def synthesize(self, text: str, *, language: str, profile: VoiceProfile) -> SpeechResult:
        return await asyncio.to_thread(self._synthesize_blocking, text, profile)

    def _synthesize_blocking(self, text: str, profile: VoiceProfile) -> SpeechResult:
        with self._lock:  # pyttsx3 engines are not thread-safe
            engine = self._engine()
            fd, path = tempfile.mkstemp(suffix=".wav")
            os.close(fd)
            try:
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
        return SpeechResult(
            audio=data, mime_type=sniff_audio_mime(data), provider=self.name, voice="system-default", spoken_text=text
        )


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


_REGISTRY: dict[str, Callable[[], TTSProvider]] = {"edge": EdgeTTS, "pyttsx3": Pyttsx3TTS}


def build_tts(config: Optional[VoiceConfig] = None) -> TTSProvider:
    """Build the TTS stack from ``config.tts_providers`` (default: edge, then pyttsx3)."""
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

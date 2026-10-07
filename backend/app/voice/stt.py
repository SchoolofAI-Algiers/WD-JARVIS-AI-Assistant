"""Speech-to-text layer."""
from __future__ import annotations

import importlib.util
import io
import logging
import math
import threading
import time
from abc import ABC, abstractmethod
from typing import Any, Callable, Optional, Sequence

from .models import STTError, TranscriptionResult, VoiceConfig, VoiceErrorCode

logger = logging.getLogger("jarvis.voice.stt")


# Helpers
def validate_audio(audio: Optional[bytes], *, min_bytes: int, max_bytes: int) -> None:
    """Reject recordings that are empty, accidental taps, or too large."""
    size = len(audio) if audio else 0
    if size == 0 or size < min_bytes:
        raise STTError(VoiceErrorCode.EMPTY_AUDIO, f"{size} bytes received (minimum {min_bytes})")
    if size > max_bytes:
        raise STTError(VoiceErrorCode.AUDIO_TOO_LARGE, f"{size} bytes received (maximum {max_bytes})")


def segment_confidence(avg_logprob: float) -> float:
    """Map Whisper's average log-probability to a rough 0..1 confidence."""
    return max(0.0, min(1.0, math.exp(avg_logprob)))


def summarize_segments(segments: Sequence[Any], no_speech_threshold: float) -> tuple[str, Optional[float]]:
    """Join Whisper segments into (text, confidence) """
    parts: list[str] = []
    weighted = 0.0
    total = 0.0
    for seg in segments:
        text = (getattr(seg, "text", "") or "").strip()
        if not text:
            continue
        avg_logprob = float(getattr(seg, "avg_logprob", 0.0))
        if float(getattr(seg, "no_speech_prob", 0.0)) > no_speech_threshold and avg_logprob < -1.0:
            continue
        parts.append(text)
        weight = max(float(getattr(seg, "end", 0.0)) - float(getattr(seg, "start", 0.0)), 0.05)
        weighted += weight * segment_confidence(avg_logprob)
        total += weight
    confidence = round(weighted / total, 3) if total else None
    return " ".join(parts).strip(), confidence


# Provider interface
class STTProvider(ABC):
    name: str = "stt"

    @abstractmethod
    def transcribe(
        self, audio: bytes, mime_type: str = "audio/webm", language: Optional[str] = None
    ) -> TranscriptionResult:
        """Blocking transcription of one complete utterance. Raises ``STTError``."""

    def is_available(self) -> bool:
        """Cheap check (no heavy loading) used by health endpoints and the UI."""
        return True

    def warmup(self) -> None:
        """Optional: load models ahead of the first request to avoid a slow first turn."""

    def health(self) -> dict[str, Any]:
        return {"available": self.is_available()}


# Local Whisper (faster-whisper)
class FasterWhisperSTT(STTProvider):
    name = "faster-whisper"

    def __init__(
        self,
        model_size: str = "small",
        device: str = "cpu",
        compute_type: str = "int8",
        language: Optional[str] = None,
        no_speech_threshold: float = 0.6,
        *,
        model_factory: Optional[Callable[[], Any]] = None,
        retry_after_s: float = 60.0,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.language = language
        self.no_speech_threshold = no_speech_threshold
        self._custom_factory = model_factory is not None
        self._factory = model_factory or self._default_factory
        self._retry_after_s = retry_after_s
        self._clock = clock

        self._model: Any = None
        self._load_lock = threading.Lock()
        self._infer_lock = threading.Lock()  # one inference at a time on a laptop CPU
        self._failed_at: Optional[float] = None
        self._permanent_failure: Optional[str] = None

    @classmethod
    def from_config(cls, config: VoiceConfig) -> "FasterWhisperSTT":
        return cls(
            model_size=config.stt_model_size,
            device=config.stt_device,
            compute_type=config.stt_compute_type,
            language=config.stt_language,
            no_speech_threshold=config.stt_no_speech_threshold,
        )

    # lifecycle
    def _default_factory(self) -> Any:
        from faster_whisper import WhisperModel  # ImportError is handled by _get_model

        return WhisperModel(self.model_size, device=self.device, compute_type=self.compute_type)

    def is_available(self) -> bool:
        if self._permanent_failure:
            return False
        if self._custom_factory:
            return True
        return importlib.util.find_spec("faster_whisper") is not None

    def warmup(self) -> None:
        self._get_model()

    def health(self) -> dict[str, Any]:
        if self._permanent_failure or not self.is_available():
            status = "unavailable"
        elif self._model is not None:
            status = "ready"
        elif self._failed_at is not None:
            status = "load_failed"
        else:
            status = "not_loaded"
        return {"available": self.is_available(), "ready": self._model is not None, "status": status}
    
    def _get_model(self) -> Any:
        with self._load_lock:
            if self._model is not None:
                return self._model
            if self._permanent_failure:
                raise STTError(VoiceErrorCode.STT_UNAVAILABLE, self._permanent_failure)
            if self._failed_at is not None and self._clock() - self._failed_at < self._retry_after_s:
                raise STTError(VoiceErrorCode.STT_UNAVAILABLE, "model failed to load recently; retrying later")
            try:
                logger.info("loading faster-whisper model '%s' (%s, %s)", self.model_size, self.device, self.compute_type)
                self._model = self._factory()
            except ImportError as exc:
                self._permanent_failure = f"faster-whisper is not installed ({exc})"
                raise STTError(VoiceErrorCode.STT_UNAVAILABLE, self._permanent_failure) from exc
            except Exception as exc:  # model download failed, out of memory, bad device...
                self._failed_at = self._clock()
                logger.exception("could not load Whisper model '%s'", self.model_size)
                raise STTError(
                    VoiceErrorCode.STT_UNAVAILABLE, f"could not load model '{self.model_size}': {exc}"
                ) from exc
            self._failed_at = None
            return self._model

    # inference
    def transcribe(
        self, audio: bytes, mime_type: str = "audio/webm", language: Optional[str] = None
    ) -> TranscriptionResult:
        model = self._get_model()
        try:
            with self._infer_lock:
                segments, info = model.transcribe(
                    io.BytesIO(audio),
                    language=language or self.language,
                    beam_size=1,  # fastest; good enough for short commands
                    vad_filter=True, 
                    condition_on_previous_text=False,
                )
                segments = list(segments)  # the generator decodes lazily: errors surface here
        except Exception as exc:
            # PyAV raises its own exception types for corrupt / unsupported containers.
            if type(exc).__module__.split(".")[0] == "av":
                raise STTError(VoiceErrorCode.AUDIO_UNREADABLE, f"{type(exc).__name__}: {exc}") from exc
            raise STTError(VoiceErrorCode.STT_UNAVAILABLE, f"{type(exc).__name__}: {exc}") from exc

        text, confidence = summarize_segments(segments, self.no_speech_threshold)
        logger.debug("faster-whisper produced %d chars (confidence=%s)", len(text), confidence)
        return TranscriptionResult(
            text=text,
            language=getattr(info, "language", None),
            confidence=confidence,
            duration_s=getattr(info, "duration", None),
            provider=self.name,
        )


# Fallback chain + factory
_FALLBACK_CODES = frozenset({VoiceErrorCode.STT_UNAVAILABLE, VoiceErrorCode.STT_TIMEOUT})


class FallbackSTT(STTProvider):
    """Try several providers in order (e.g. local Whisper, then a hosted API)"""

    def __init__(self, providers: Sequence[STTProvider]):
        if not providers:
            raise ValueError("FallbackSTT needs at least one provider")
        self.providers = list(providers)
        self.name = "fallback(" + ">".join(p.name for p in self.providers) + ")"

    def is_available(self) -> bool:
        return any(p.is_available() for p in self.providers)

    def warmup(self) -> None:
        for provider in self.providers:
            try:
                provider.warmup()
            except Exception as exc:  # warm-up must never stop the app from starting
                logger.warning("STT warm-up failed for %s: %s", provider.name, exc)

    def transcribe(
        self, audio: bytes, mime_type: str = "audio/webm", language: Optional[str] = None
    ) -> TranscriptionResult:
        last: Optional[STTError] = None
        for provider in self.providers:
            try:
                return provider.transcribe(audio, mime_type, language)
            except STTError as exc:
                if exc.code not in _FALLBACK_CODES:
                    raise
                logger.warning("STT provider %s unavailable: %s", provider.name, exc.detail)
                last = exc
        raise STTError(VoiceErrorCode.STT_UNAVAILABLE, f"all STT providers failed; last error: {last.detail if last else 'n/a'}")


def build_stt(config: Optional[VoiceConfig] = None) -> STTProvider:
    """Default STT stack. Add hosted providers to the ``FallbackSTT`` list here."""
    config = config or VoiceConfig()
    return FasterWhisperSTT.from_config(config)
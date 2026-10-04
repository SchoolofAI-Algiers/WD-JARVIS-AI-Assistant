"""Data models, configuration and errors for the J.A.R.V.I.S. voice layer.
* ``VoiceState`` / ``VoiceEvent``   -> the status the dashboard renders
* ``TranscriptionResult``           -> what STT returns
* ``SpeechResult``                  -> what TTS returns
* ``VoiceTurnResult``               -> what one full voice turn returns to the API
* ``VoiceError`` (+ subclasses)     -> typed failures with a user-facing message
* ``VoiceProfile`` / ``VoiceConfig``-> the J.A.R.V.I.S. voice identity and tunables
"""
from __future__ import annotations

import base64
import os
import time
from enum import Enum
from typing import Any, Mapping, Optional

from pydantic import BaseModel, Field, field_serializer


# Interface state (consumed by the dashboard)
class VoiceState(str, Enum):
    """Assistant status labels shown by the J.A.R.V.I.S. visualizer."""
    IDLE = "idle"
    LISTENING = "listening"  
    THINKING = "thinking"  # waiting for the assistant
    USING_TOOL = "using_tool"
    SPEAKING = "speaking"
    ERROR = "error"


class VoiceEvent(BaseModel):
    """A single state change, ready to be pushed to the UI."""
    state: VoiceState
    detail: Optional[str] = None
    conversation_id: Optional[str] = None
    timestamp: float = Field(default_factory=time.time)


# Errors
class VoiceErrorCode(str, Enum):
    EMPTY_AUDIO = "empty_audio"
    AUDIO_TOO_LARGE = "audio_too_large"
    AUDIO_UNREADABLE = "audio_unreadable"
    NO_SPEECH = "no_speech"
    LOW_CONFIDENCE = "low_confidence"
    STT_UNAVAILABLE = "stt_unavailable"
    STT_TIMEOUT = "stt_timeout"
    EMPTY_TEXT = "empty_text"
    ASSISTANT_UNAVAILABLE = "assistant_unavailable"
    ASSISTANT_TIMEOUT = "assistant_timeout"
    TTS_UNAVAILABLE = "tts_unavailable"
    TTS_TIMEOUT = "tts_timeout"
    INTERNAL = "internal_error"


# One place to tune the assistant's voice persona for failures.
USER_MESSAGES: dict[VoiceErrorCode, str] = {
    VoiceErrorCode.EMPTY_AUDIO: "I didn't hear anything. Hold the microphone button while you speak, or type your request.",
    VoiceErrorCode.AUDIO_TOO_LARGE: "That recording is too long for me to process. Please try a shorter request.",
    VoiceErrorCode.AUDIO_UNREADABLE: "I couldn't read that recording. Please try again, or type your request.",
    VoiceErrorCode.NO_SPEECH: "I didn't catch any speech. Please try again, or type your request.",
    VoiceErrorCode.LOW_CONFIDENCE: "I didn't quite catch that. Could you repeat it, or type it instead?",
    VoiceErrorCode.STT_UNAVAILABLE: "My speech recognition is offline at the moment. You can still type your request.",
    VoiceErrorCode.STT_TIMEOUT: "Speech recognition is taking too long. Please try again, or type your request.",
    VoiceErrorCode.EMPTY_TEXT: "I didn't receive a request. Please try again.",
    VoiceErrorCode.ASSISTANT_UNAVAILABLE: "I'm having trouble reaching my core systems. Please try again in a moment.",
    VoiceErrorCode.ASSISTANT_TIMEOUT: "That is taking longer than expected. Please try again in a moment.",
    VoiceErrorCode.TTS_UNAVAILABLE: "My voice is unavailable right now, so I'll reply in text.",
    VoiceErrorCode.TTS_TIMEOUT: "My voice is taking too long, so I'll reply in text.",
    VoiceErrorCode.INTERNAL: "Something went wrong on my side. Please try again.",
}

# Errors where "try again" is a sensible thing to tell the user.
RETRYABLE_CODES = frozenset(
    {
        VoiceErrorCode.EMPTY_AUDIO,
        VoiceErrorCode.AUDIO_UNREADABLE,
        VoiceErrorCode.NO_SPEECH,
        VoiceErrorCode.LOW_CONFIDENCE,
        VoiceErrorCode.STT_TIMEOUT,
        VoiceErrorCode.EMPTY_TEXT,
        VoiceErrorCode.ASSISTANT_UNAVAILABLE,
        VoiceErrorCode.ASSISTANT_TIMEOUT,
        VoiceErrorCode.INTERNAL,
    }
)


class VoiceErrorInfo(BaseModel):
    """Serializable error description sent to the frontend."""

    code: VoiceErrorCode
    message: str  # safe to show / speak to the user
    retryable: bool = False


class VoiceError(Exception):
    """Base class for every expected voice failure."""

    def __init__(self, code: VoiceErrorCode, detail: str = ""):
        self.code = code
        self.detail = detail or code.value
        super().__init__(f"[{code.value}] {self.detail}")

    @property
    def user_message(self) -> str:
        return USER_MESSAGES[self.code]

    @property
    def retryable(self) -> bool:
        return self.code in RETRYABLE_CODES

    def to_info(self) -> VoiceErrorInfo:
        return VoiceErrorInfo(code=self.code, message=self.user_message, retryable=self.retryable)


class STTError(VoiceError):
    """Speech recognition failed."""


class TTSError(VoiceError):
    """Speech synthesis failed."""


class AssistantError(VoiceError):
    """The assistant core could not produce a reply."""

# Results
class TranscriptionResult(BaseModel):
    text: str
    language: Optional[str] = None
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    duration_s: Optional[float] = None
    provider: str = "unknown"


class SpeechResult(BaseModel):
    audio: bytes  # raw audio in Python; STANDARD base64 text in JSON
    mime_type: str
    provider: str
    voice: Optional[str] = None
    spoken_text: str = ""
    truncated: bool = False  # True if the spoken text is a shortened version of the reply

    @field_serializer("audio", when_used="json")
    def _audio_as_base64(self, value: bytes) -> str:
        # Python's b64decode, the browser's atob() and data: URLs all reject or silently corrupt.
        return base64.b64encode(value).decode("ascii")


class AssistantReply(BaseModel):
    """What the Assistant Core returned for one message (text + its metadata)."""
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)  # tool calls, RAG sources... passed to the UI untouched


class VoiceTurnResult(BaseModel):
    """Everything the API returns for one voice (or text->voice) turn."""
    ok: bool  
    conversation_id: Optional[str] = None
    transcript: Optional[TranscriptionResult] = None
    reply_text: str = ""  # assistant reply, or the error message when ok is False
    metadata: dict[str, Any] = Field(default_factory=dict)  # the assistant's own metadata (same as /chat)
    speech: Optional[SpeechResult] = None
    degraded: bool = False  # reply is valid but spoken output is unavailable (text only)
    needs_retry: bool = False  # UI should invite the user to speak/type again
    error: Optional[VoiceErrorInfo] = None
    timings_ms: dict[str, float] = Field(default_factory=dict)  # stt_ms / assistant_ms / tts_ms / total_ms


# Voice identity + configuration
class VoiceProfile(BaseModel):
    """The J.A.R.V.I.S. voice"""

    name: str = "jarvis"
    default_language: str = "en"
    voices: dict[str, str] = Field(
        default_factory=lambda: {
            "en": "en-GB-RyanNeural",
            "fr": "fr-FR-HenriNeural",
            "ar": "ar-DZ-IsmaelNeural",
        }
    )
    rate: str = "-5%" 
    pitch: str = "-3Hz"
    volume: str = "+0%"
    offline_rate_wpm: int = 165  # used by the offline pyttsx3 fallback

    def voice_for(self, language: Optional[str]) -> str:
        base = (language or self.default_language).lower().split("-")[0]
        return self.voices.get(base) or self.voices[self.default_language]


class VoiceConfig(BaseModel):

    # speech-to-text
    stt_model_size: str = "base"  # tiny / base / small / medium ; benchmark on the event laptop
    stt_device: str = "auto"
    stt_compute_type: str = "int8"
    stt_language: Optional[str] = None  
    stt_min_confidence: float = Field(default=0.40, ge=0.0, le=1.0)
    stt_no_speech_threshold: float = Field(default=0.6, ge=0.0, le=1.0)
    stt_timeout_s: float = Field(default=20.0, gt=0)

    # audio guard rails
    min_audio_bytes: int = Field(default=1_000, ge=0)  # shorter = accidental tap on the mic button
    max_audio_bytes: int = Field(default=10 * 1024 * 1024, gt=0)

    # assistant
    assistant_timeout_s: float = Field(default=30.0, gt=0)

    # text-to-speech
    tts_providers: list[str] = Field(default_factory=lambda: ["edge", "pyttsx3"])  # tried in order
    tts_provider_timeout_s: float = Field(default=8.0, gt=0)
    tts_timeout_s: float = Field(default=20.0, gt=0)
    tts_max_spoken_chars: int = Field(default=600, gt=0)

    profile: VoiceProfile = Field(default_factory=VoiceProfile)

    @classmethod
    def from_env(cls, env: Optional[Mapping[str, str]] = None) -> "VoiceConfig":
        env = os.environ if env is None else env
        overrides: dict[str, object] = {}
        for name in cls.model_fields:
            if name == "profile":
                continue
            raw = env.get(f"VOICE_{name.upper()}")
            if raw is None or raw.strip() == "":
                continue
            if name == "tts_providers":
                overrides[name] = [part.strip() for part in raw.split(",") if part.strip()]
            else:
                overrides[name] = raw.strip() 
        return cls(**overrides)
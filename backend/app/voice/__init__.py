"""J.A.R.V.I.S. voice layer: speech input (STT), speech output (TTS) and the turn pipeline"""
from .models import (
    AssistantReply,
    SpeechResult,
    TranscriptionResult,
    VoiceConfig,
    VoiceError,
    VoiceErrorCode,
    VoiceErrorInfo,
    VoiceEvent,
    VoiceProfile,
    VoiceState,
    VoiceTurnResult,
)
from .pipeline import AssistantBackend, CallableAssistant, VoicePipeline, build_pipeline
from .stt import FallbackSTT, FasterWhisperSTT, STTProvider, build_stt
from .tts import EdgeTTS, FallbackTTS, Pyttsx3TTS, TTSProvider, build_tts

__all__ = [
    "AssistantBackend",
    "AssistantReply",
    "CallableAssistant",
    "EdgeTTS",
    "FallbackSTT",
    "FallbackTTS",
    "FasterWhisperSTT",
    "Pyttsx3TTS",
    "STTProvider",
    "SpeechResult",
    "TTSProvider",
    "TranscriptionResult",
    "VoiceConfig",
    "VoiceError",
    "VoiceErrorCode",
    "VoiceErrorInfo",
    "VoiceEvent",
    "VoicePipeline",
    "VoiceProfile",
    "VoiceState",
    "VoiceTurnResult",
    "build_pipeline",
    "build_stt",
    "build_tts",
]

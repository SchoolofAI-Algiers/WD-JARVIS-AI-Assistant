"""The voice turn pipeline:  audio -> STT -> assistant -> TTS.

Failure policy (so the live demo never dead-ends):
* Bad / silent / low-confidence audio -> ``ok=False, needs_retry=True`` with a friendly
  "please repeat or type it" message (spoken too when TTS works).
* STT down                            -> ``ok=False`` and a message pointing to text input.
* Assistant down / too slow           -> ``ok=False`` with a clear message, never a hang.
* TTS down                            -> ``ok=True, degraded=True``: the text reply is still
  returned, only the audio is missing.
"""
from __future__ import annotations

import asyncio
import inspect
import logging
import time
from typing import Any, Awaitable, Callable, Optional, Protocol, Union

from .models import (
    AssistantError,
    AssistantReply,
    SpeechResult,
    STTError,
    TranscriptionResult,
    TTSError,
    VoiceConfig,
    VoiceError,
    VoiceErrorCode,
    VoiceEvent,
    VoiceState,
    VoiceTurnResult,
)
from .stt import STTProvider, build_stt, validate_audio
from .tts import TTSProvider, build_tts, detect_language, prepare_spoken_text

logger = logging.getLogger("jarvis.voice.pipeline")

StateCallback = Callable[[VoiceEvent], Union[None, Awaitable[None]]]


# Assistant side
class AssistantBackend(Protocol):
    """What the voice layer needs from the Assistant Core: text in, reply out"""

    async def reply(self, text: str, conversation_id: Optional[str] = None) -> Union[str, AssistantReply]: ...


class CallableAssistant:
    def __init__(self, fn: Callable[[str, Optional[str]], Any]):
        self._fn = fn

    async def reply(self, text: str, conversation_id: Optional[str] = None) -> Union[str, AssistantReply]:
        if inspect.iscoroutinefunction(self._fn):
            result = await self._fn(text, conversation_id)
        else:
            result = await asyncio.to_thread(self._fn, text, conversation_id)
            if inspect.isawaitable(result):
                result = await result
        if not isinstance(result, (str, AssistantReply)):
            raise AssistantError(
                VoiceErrorCode.ASSISTANT_UNAVAILABLE,
                f"assistant returned {type(result).__name__}, expected str or AssistantReply",
            )
        return result


# Pipeline
class VoicePipeline:
    def __init__(
        self,
        stt: STTProvider,
        tts: TTSProvider,
        assistant: AssistantBackend,
        config: Optional[VoiceConfig] = None,
        on_state: Optional[StateCallback] = None,
    ):
        self.stt = stt
        self.tts = tts
        self.assistant = assistant
        self.config = config or VoiceConfig()
        self.on_state = on_state

    # public API
    async def process_audio(
        self,
        audio: bytes,
        mime_type: str = "audio/webm",
        *,
        conversation_id: Optional[str] = None,
        language: Optional[str] = None,
        speak: bool = True,
    ) -> VoiceTurnResult:
        """Full voice turn: recorded utterance in, transcript + reply + speech out."""
        return await self._turn(
            audio=audio, mime_type=mime_type, text=None, conversation_id=conversation_id, language=language, speak=speak
        )

    async def process_text(
        self,
        text: str,
        *,
        conversation_id: Optional[str] = None,
        language: Optional[str] = None,
        speak: bool = True,
    ) -> VoiceTurnResult:
        """Typed input with a spoken reply (also the fallback when the microphone fails)."""
        return await self._turn(
            audio=None, mime_type="", text=text, conversation_id=conversation_id, language=language, speak=speak
        )

    async def say(
        self, text: str, *, conversation_id: Optional[str] = None, language: Optional[str] = None
    ) -> VoiceTurnResult:
        """Speak arbitrary text (greetings, announcements) without calling the assistant."""
        started = time.perf_counter()
        timings: dict[str, float] = {}
        speech, tts_error = await self._speak_safely(text, language, conversation_id, timings)
        await self._emit(VoiceState.IDLE, conversation_id)
        timings["total_ms"] = _elapsed_ms(started)
        return VoiceTurnResult(
            ok=tts_error is None,
            conversation_id=conversation_id,
            reply_text=text,
            speech=speech,
            degraded=tts_error is not None,
            error=tts_error.to_info() if tts_error else None,
            timings_ms=timings,
        )

    async def report_state(
        self, state: VoiceState, *, conversation_id: Optional[str] = None, detail: Optional[str] = None
    ) -> None:
        """Let other components (e.g. the tool router) publish a state such as USING_TOOL."""
        await self._emit(state, conversation_id, detail)

    async def warmup(self) -> None:
        """Load the STT model at startup so the first utterance is not slow."""
        try:
            await asyncio.to_thread(self.stt.warmup)
        except Exception as exc:
            logger.warning("voice warm-up failed (will retry lazily): %s", exc)

    def health(self) -> dict[str, Any]:
        """Report package availability separately from local model readiness."""
        return {
            "stt": {"provider": self.stt.name, **self.stt.health()},
            "tts": {"provider": self.tts.name, "available": self.tts.is_available()},
        }

    # turn orchestration
    async def _turn(
        self,
        *,
        audio: Optional[bytes],
        mime_type: str,
        text: Optional[str],
        conversation_id: Optional[str],
        language: Optional[str],
        speak: bool,
    ) -> VoiceTurnResult:
        started = time.perf_counter()
        timings: dict[str, float] = {}
        transcript: Optional[TranscriptionResult] = None
        try:
            if audio is not None:
                await self._emit(VoiceState.THINKING, conversation_id, "transcribing")
                transcript = await self._transcribe(audio, mime_type, language, timings)
                self._check_transcript(transcript)
                user_text = transcript.text.strip()
                language_hint = transcript.language or language
            else:
                user_text = (text or "").strip()
                language_hint = language
                if not user_text:
                    raise VoiceError(VoiceErrorCode.EMPTY_TEXT, "blank text")

            assistant_reply = await self._ask_assistant(user_text, conversation_id, timings)
            reply = assistant_reply.text

            speech, tts_error = None, None
            if speak:
                speech, tts_error = await self._speak_safely(reply, language_hint, conversation_id, timings)
            await self._emit(VoiceState.IDLE, conversation_id)

            timings["total_ms"] = _elapsed_ms(started)
            logger.info(
                "voice turn ok conv=%s degraded=%s timings_ms=%s", conversation_id, tts_error is not None, timings
            )
            return VoiceTurnResult(
                ok=True,
                conversation_id=conversation_id,
                transcript=transcript,
                reply_text=reply,
                metadata=assistant_reply.metadata,
                speech=speech,
                degraded=tts_error is not None,
                error=tts_error.to_info() if tts_error else None,
                timings_ms=timings,
            )
        except VoiceError as exc:
            return await self._fail(exc, conversation_id, transcript, speak, timings, started)
        except Exception as exc:  # last line of defence: a voice bug must not crash the API
            logger.exception("unexpected voice pipeline failure")
            internal = VoiceError(VoiceErrorCode.INTERNAL, f"{type(exc).__name__}: {exc}")
            return await self._fail(internal, conversation_id, transcript, speak, timings, started)

    # STT step
    async def _transcribe(
        self, audio: bytes, mime_type: str, language: Optional[str], timings: dict[str, float]
    ) -> TranscriptionResult:
        validate_audio(audio, min_bytes=self.config.min_audio_bytes, max_bytes=self.config.max_audio_bytes)
        started = time.perf_counter()
        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(self.stt.transcribe, audio, mime_type, language),
                timeout=self.config.stt_timeout_s,
            )
        except asyncio.TimeoutError as exc:
            raise STTError(VoiceErrorCode.STT_TIMEOUT, f"no result after {self.config.stt_timeout_s:g}s") from exc
        except VoiceError:
            raise
        except Exception as exc:
            raise STTError(VoiceErrorCode.STT_UNAVAILABLE, f"{type(exc).__name__}: {exc}") from exc
        timings["stt_ms"] = _elapsed_ms(started)
        logger.debug("transcript: %r (confidence=%s)", result.text, result.confidence)
        return result

    def _check_transcript(self, transcript: TranscriptionResult) -> None:
        if not transcript.text.strip():
            raise STTError(VoiceErrorCode.NO_SPEECH, "empty transcript")
        if transcript.confidence is not None and transcript.confidence < self.config.stt_min_confidence:
            raise STTError(
                VoiceErrorCode.LOW_CONFIDENCE,
                f"confidence {transcript.confidence:.2f} < {self.config.stt_min_confidence:.2f}",
            )

    # assistant step
    async def _ask_assistant(
        self, text: str, conversation_id: Optional[str], timings: dict[str, float]
    ) -> AssistantReply:
        await self._emit(VoiceState.THINKING, conversation_id, "thinking")
        started = time.perf_counter()
        try:
            reply = await asyncio.wait_for(
                self.assistant.reply(text, conversation_id), timeout=self.config.assistant_timeout_s
            )
        except asyncio.TimeoutError as exc:
            raise AssistantError(
                VoiceErrorCode.ASSISTANT_TIMEOUT, f"no reply after {self.config.assistant_timeout_s:g}s"
            ) from exc
        except VoiceError:
            raise
        except Exception as exc:
            logger.exception("assistant backend failed")
            raise AssistantError(VoiceErrorCode.ASSISTANT_UNAVAILABLE, f"{type(exc).__name__}: {exc}") from exc
        timings["assistant_ms"] = _elapsed_ms(started)
        if isinstance(reply, str):
            reply = AssistantReply(text=reply)
        text = (reply.text or "").strip()
        if not text:
            raise AssistantError(VoiceErrorCode.ASSISTANT_UNAVAILABLE, "empty reply")
        return reply.model_copy(update={"text": text})

    # TTS step
    async def _speak_safely(
        self, text: str, language_hint: Optional[str], conversation_id: Optional[str], timings: dict[str, float]
    ) -> tuple[Optional[SpeechResult], Optional[VoiceError]]:
        """Synthesize speech; a TTS failure degrades to text instead of failing the turn."""
        await self._emit(VoiceState.SPEAKING, conversation_id)
        try:
            return await self._synthesize(text, language_hint, timings), None
        except VoiceError as exc:
            logger.warning("speech synthesis unavailable: %s", exc.detail)
            return None, exc

    async def _synthesize(
        self, text: str, language_hint: Optional[str], timings: dict[str, float]
    ) -> Optional[SpeechResult]:
        profile = self.config.profile
        language = detect_language(
            text, language_hint, default=profile.default_language, supported=tuple(profile.voices)
        )
        spoken, truncated = prepare_spoken_text(text, self.config.tts_max_spoken_chars, language)
        if not spoken:
            return None  
        started = time.perf_counter()
        try:
            speech = await asyncio.wait_for(
                self.tts.synthesize(spoken, language=language, profile=profile), timeout=self.config.tts_timeout_s
            )
        except asyncio.TimeoutError as exc:
            raise TTSError(VoiceErrorCode.TTS_TIMEOUT, f"no audio after {self.config.tts_timeout_s:g}s") from exc
        except VoiceError:
            raise
        except Exception as exc:
            raise TTSError(VoiceErrorCode.TTS_UNAVAILABLE, f"{type(exc).__name__}: {exc}") from exc
        timings["tts_ms"] = _elapsed_ms(started)
        return speech.model_copy(update={"truncated": truncated})

    # failure handling
    async def _fail(
        self,
        exc: VoiceError,
        conversation_id: Optional[str],
        transcript: Optional[TranscriptionResult],
        speak: bool,
        timings: dict[str, float],
        started: float,
    ) -> VoiceTurnResult:
        info = exc.to_info()
        logger.warning("voice turn failed conv=%s code=%s detail=%s", conversation_id, exc.code.value, exc.detail)
        await self._emit(VoiceState.ERROR, conversation_id, exc.code.value)

        speech: Optional[SpeechResult] = None
        if speak: 
            try:
                speech = await self._synthesize(info.message, self.config.profile.default_language, timings)
            except Exception as tts_exc:
                logger.debug("could not speak the error message: %s", tts_exc)

        timings["total_ms"] = _elapsed_ms(started)
        return VoiceTurnResult(
            ok=False,
            conversation_id=conversation_id,
            transcript=transcript,
            reply_text=info.message,
            speech=speech,
            needs_retry=info.retryable,
            error=info,
            timings_ms=timings,
        )

    # UI state
    async def _emit(self, state: VoiceState, conversation_id: Optional[str], detail: Optional[str] = None) -> None:
        if self.on_state is None:
            return
        event = VoiceEvent(state=state, detail=detail, conversation_id=conversation_id)
        try:
            outcome = self.on_state(event)
            if inspect.isawaitable(outcome):
                await outcome
        except Exception:  # a broken dashboard callback must never break the turn
            logger.warning("voice state callback failed", exc_info=True)


def _elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 1)


def build_pipeline(
    assistant: AssistantBackend,
    config: Optional[VoiceConfig] = None,
    on_state: Optional[StateCallback] = None,
) -> VoicePipeline:
    """Default wiring: local Whisper for STT, Edge neural voice (+ offline fallback) for TTS."""
    config = config or VoiceConfig.from_env()
    return VoicePipeline(build_stt(config), build_tts(config), assistant, config=config, on_state=on_state)

"""Voice endpoints
    POST /voice/turn     
    POST /voice/speak    
    GET  /voice/health  
"""
from __future__ import annotations

import asyncio
import uuid
from functools import lru_cache
from typing import Any, Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile
from pydantic import BaseModel, Field

from app.voice import AssistantReply, VoicePipeline, VoiceTurnResult, build_pipeline

router = APIRouter(prefix="/voice", tags=["voice"])


class AssistantCoreAdapter:
    """Lets the voice pipeline talk to the existing Assistant Core."""

    def __init__(self, assistant: Any = None):
        self._assistant = assistant

    def _core(self) -> Any:
        if self._assistant is None: 
            from app.core.assistant import assistant

            self._assistant = assistant
        return self._assistant

    async def reply(self, text: str, conversation_id: Optional[str] = None) -> AssistantReply:
        result = await asyncio.to_thread(self._core().process, conversation_id=conversation_id, message=text)
        return AssistantReply(text=result["message"], metadata=result.get("metadata") or {})


@lru_cache(maxsize=1)
def get_voice_pipeline() -> VoicePipeline:
    """One shared pipeline per process (the Whisper model is loaded once)."""
    return build_pipeline(AssistantCoreAdapter())


async def warmup_voice() -> None:
    """Optional: call from the app's startup handler so the first utterance is not slow."""
    await get_voice_pipeline().warmup()


async def warmup_voice_tts() -> None:
    """Preload the speech voices (called in the background at server start)."""
    await get_voice_pipeline().warmup_tts()


class SpeakRequest(BaseModel):
    text: str = Field(min_length=1)
    language: Optional[str] = None  # "en" / "fr" / "ar"; detected from the text when omitted
    conversation_id: Optional[str] = None


@router.post("/turn", response_model=VoiceTurnResult)
async def voice_turn(
    audio: UploadFile = File(..., description="One recorded utterance (webm/ogg/mp4/wav)"),
    conversation_id: Optional[str] = Form(None),
    language: Optional[str] = Form(None, description="Force the STT language, e.g. 'fr'"),
    speak: bool = Form(True, description="Set to false to get text only"),
    pipeline: VoicePipeline = Depends(get_voice_pipeline),
) -> VoiceTurnResult:
    data = await audio.read(pipeline.config.max_audio_bytes + 1)  # never buffer more than the limit + 1 byte
    return await pipeline.process_audio(
        data,
        audio.content_type or "audio/webm",
        conversation_id=conversation_id or uuid.uuid4().hex,
        language=language or None,
        speak=speak,
    )


@router.post("/speak", response_model=VoiceTurnResult)
async def voice_speak(
    request: SpeakRequest, pipeline: VoicePipeline = Depends(get_voice_pipeline)
) -> VoiceTurnResult:
    return await pipeline.say(request.text, conversation_id=request.conversation_id, language=request.language)


@router.get("/health")
async def voice_health(pipeline: VoicePipeline = Depends(get_voice_pipeline)) -> dict[str, Any]:
    return pipeline.health()
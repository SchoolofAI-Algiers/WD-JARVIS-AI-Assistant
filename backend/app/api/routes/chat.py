from fastapi import APIRouter

from app.core.assistant import assistant
from app.models.chat import ChatRequest, ChatResponse


router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    result = assistant.process(
        conversation_id=request.conversation_id,
        message=request.message,
    )

    return ChatResponse(
        conversation_id=request.conversation_id,
        status="complete",
        message=result["message"],
        metadata=result["metadata"],
    )
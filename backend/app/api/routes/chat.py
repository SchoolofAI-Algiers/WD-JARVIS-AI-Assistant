from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class ChatRequest(BaseModel):
    conversation_id: str
    message: str


class ChatResponse(BaseModel):
    conversation_id: str
    status: str
    message: str
    metadata: dict


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    return ChatResponse(
        conversation_id=request.conversation_id,
        status="complete",
        message=f"JARVIS received: {request.message}",
        metadata={
            "type": "mock"
        }
    )
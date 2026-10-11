from __future__ import annotations

from datetime import datetime
from typing import Protocol

from app.core.llm.client import LLMClient
from app.core.llm.prompts import build_system_prompt, build_user_prompt
from app.memory.conversation import ConversationMemory, conversation_memory


class _TextGenerator(Protocol):
    def generate(
        self,
        prompt: str,
        *,
        system_instruction: str | None = None,
        temperature: float = 0.7,
        max_output_tokens: int = 1024,
    ) -> str: ...


class LLMService:
    """Application service for contextual text generation."""

    def __init__(
        self,
        *,
        client: _TextGenerator | None = None,
        memory: ConversationMemory | None = None,
    ) -> None:
        self._client = client or LLMClient()
        self._memory = memory or conversation_memory

    def generate_response(
        self,
        conversation_id: str,
        message: str,
        retrieved_context: str = "",
    ) -> str:
        """Generate a response using the conversation's short-term history
        and, for SOAI questions, the passages found by the RAG."""
        if not conversation_id or not conversation_id.strip():
            raise ValueError("conversation_id must not be empty")

        history = self._memory.get_messages(conversation_id)
        prompt = build_user_prompt(message, history)
        history_text = "\n".join(
            f"{item.role.upper()}: {item.content}"
            for item in history
            if item.content.strip()
        )
        return self._client.generate(
            prompt,
            system_instruction=build_system_prompt(
                current_datetime=datetime.now().astimezone().isoformat(),
                retrieved_context=retrieved_context,
                conversation_history=history_text,
            ),
        )


llm_service = LLMService()
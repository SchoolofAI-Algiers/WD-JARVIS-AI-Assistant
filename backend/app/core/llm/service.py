from __future__ import annotations

from typing import Protocol

from app.core.llm.client import LLMClient
from app.core.llm.prompts import SYSTEM_PROMPT, build_user_prompt
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
    ) -> str:
        """Generate a response using the conversation's short-term history."""
        if not conversation_id or not conversation_id.strip():
            raise ValueError("conversation_id must not be empty")

        prompt = build_user_prompt(
            message,
            self._memory.get_messages(conversation_id),
        )
        return self._client.generate(
            prompt,
            system_instruction=SYSTEM_PROMPT,
        )


llm_service = LLMService()
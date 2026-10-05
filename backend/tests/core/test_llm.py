from __future__ import annotations

import sys

from app.core.llm.client import LLMError
from app.core.llm.service import LLMService
from app.memory.conversation import ConversationMemory


def run_manual_chat() -> None:
    """Run an interactive chat through the real LLM service."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    memory = ConversationMemory()
    service = LLMService(memory=memory)
    conversation_id = "manual-system-prompt-test"

    print("Manual LLM service test")
    print("The system prompt is supplied internally by LLMService.")
    print("Conversation history is preserved between messages.")
    print("Commands: /clear starts a new conversation, /exit quits.\n")

    while True:
        try:
            message = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            return

        if not message:
            continue

        if message == "/exit":
            print("Exiting.")
            return

        if message == "/clear":
            memory.clear(conversation_id)
            print("Conversation history cleared.\n")
            continue

        try:
            response = service.generate_response(
                conversation_id=conversation_id,
                message=message,
            )
        except LLMError as error:
            print(f"ERROR: {error}")
            print("Check your API keys and provider connectivity.\n")
            continue

        print(f"J.A.R.V.I.S.: {response}\n")
        memory.add_message(conversation_id, "user", message)
        memory.add_message(conversation_id, "assistant", response)


if __name__ == "__main__":
    run_manual_chat()

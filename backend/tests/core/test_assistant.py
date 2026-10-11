from uuid import uuid4

import pytest

from app.core.assistant import Assistant
from app.memory.conversation import conversation_memory


@pytest.fixture
def conversation_id():
    value = f"memory-context-{uuid4().hex}"
    yield value
    conversation_memory.clear(value)


def test_assistant_passes_history_and_current_message_to_generation(conversation_id, monkeypatch):
    conversation_memory.add_message(
        conversation_id, "user", "Earlier question"
    )
    conversation_memory.add_message(
        conversation_id, "assistant", "Earlier answer"
    )

    assistant = Assistant()
    captured = {}

    def generate_response(
        conversation_id,
        message,
        retrieved_context="",
    ):
        captured["conversation_id"] = conversation_id
        captured["message"] = message
        captured["retrieved_context"] = retrieved_context
        return "Generated response"

    monkeypatch.setattr(
        assistant.llm,
        "generate_response",
        generate_response,
    )

    result = assistant.process(
        conversation_id,
        "Current question",
    )

    assert result["message"] == "Generated response"

    assert captured["conversation_id"] == conversation_id
    assert captured["message"] == "Current question"

    stored_messages = conversation_memory.get_messages(
        conversation_id
    )

    assert [
        (message.role, message.content)
        for message in stored_messages
    ] == [
        ("user", "Earlier question"),
        ("assistant", "Earlier answer"),
        ("user", "Current question"),
        ("assistant", "Generated response"),
    ]


def test_assistant_keeps_tool_routing_ahead_of_context_generation(
    conversation_id, monkeypatch
):
    assistant = Assistant()
    monkeypatch.setattr(
        "app.core.assistant.tool_router.detect_tool",
        lambda message: "calculator",
    )
    monkeypatch.setattr(
        "app.core.assistant.tool_router.execute",
        lambda tool_name, message: {
            "tool": "calculator",
            "expression": "2 + 2",
            "result": 4,
        },
    )

    def unexpected_context_build(*args, **kwargs):
        pytest.fail("Tool requests should not build conversational context")

    monkeypatch.setattr(assistant.context_builder, "build", unexpected_context_build)

    result = assistant.process(conversation_id, "Calculate 2 + 2")

    assert result == {
        "message": "2 + 2 = 4",
        "metadata": {"type": "tool", "tool": "calculator"},
    }
    assert [message.role for message in conversation_memory.get_messages(conversation_id)] == [
        "user",
        "assistant",
    ]


def test_assistant_recall_still_uses_the_previous_user_message(conversation_id):
    assistant = Assistant()

    assistant.process(conversation_id, "My favorite color is blue")
    result = assistant.process(conversation_id, "What did I just say?")

    assert result["message"] == 'You previously said: "My favorite color is blue"'

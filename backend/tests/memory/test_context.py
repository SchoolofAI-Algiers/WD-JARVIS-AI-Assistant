from app.memory.context import ContextBuilder
from app.models.chat import ChatMessage


def test_context_builder_includes_current_message_for_empty_history():
    context = ContextBuilder().build([], "Hello")

    assert [(message.role, message.content) for message in context] == [
        ("user", "Hello")
    ]


def test_context_builder_preserves_one_previous_message_before_current():
    previous = [ChatMessage(role="user", content="Earlier question")]

    context = ContextBuilder().build(previous, "Current question")

    assert [(message.role, message.content) for message in context] == [
        ("user", "Earlier question"),
        ("user", "Current question"),
    ]


def test_context_builder_preserves_chronological_order():
    previous = [
        ChatMessage(role="user", content="First"),
        ChatMessage(role="assistant", content="First answer"),
        ChatMessage(role="user", content="Second"),
        ChatMessage(role="assistant", content="Second answer"),
    ]

    context = ContextBuilder().build(previous, "Third")

    assert [message.content for message in context] == [
        "First",
        "First answer",
        "Second",
        "Second answer",
        "Third",
    ]


def test_context_builder_does_not_mutate_history_and_avoids_trailing_duplicate():
    previous = [
        ChatMessage(role="user", content="Earlier"),
        ChatMessage(role="user", content="Current"),
    ]
    original_previous = list(previous)

    context = ContextBuilder().build(previous, "Current")

    assert context is not previous
    assert context == original_previous
    assert previous == original_previous
    assert sum(message.content == "Current" for message in context) == 1


def test_context_builder_caps_context_at_the_configured_message_limit():
    previous = [
        ChatMessage(role="user", content=f"Message {index}")
        for index in range(4)
    ]

    context = ContextBuilder(max_messages=3).build(previous, "Current")

    assert [message.content for message in context] == [
        "Message 2",
        "Message 3",
        "Current",
    ]

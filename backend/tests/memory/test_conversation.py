from app.memory.conversation import ConversationMemory


def test_conversation_memory_keeps_only_the_latest_message_limit():
    memory = ConversationMemory(max_messages=3)

    for index in range(5):
        memory.add_message("conversation", "user", f"Message {index}")

    assert [message.content for message in memory.get_messages("conversation")] == [
        "Message 2",
        "Message 3",
        "Message 4",
    ]


def test_conversation_memory_keeps_conversation_ids_isolated():
    memory = ConversationMemory()
    memory.add_message("first", "user", "First conversation")
    memory.add_message("second", "user", "Second conversation")

    assert [message.content for message in memory.get_messages("first")] == [
        "First conversation"
    ]
    assert [message.content for message in memory.get_messages("second")] == [
        "Second conversation"
    ]


def test_conversation_memory_can_clear_one_conversation():
    memory = ConversationMemory()
    memory.add_message("first", "user", "Keep this")
    memory.add_message("second", "user", "Clear this")

    memory.clear("second")

    assert memory.get_messages("second") == []
    assert [message.content for message in memory.get_messages("first")] == [
        "Keep this"
    ]

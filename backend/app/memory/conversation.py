from typing import Dict, List

from app.models.chat import ChatMessage


class ConversationMemory:
    def __init__(self, max_messages: int = 20):
        self.conversations: Dict[str, List[ChatMessage]] = {}
        self.max_messages = max_messages

    def get_messages(self, conversation_id: str) -> List[ChatMessage]:
        return self.conversations.get(conversation_id, [])

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
    ) -> None:
        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = []

        self.conversations[conversation_id].append(
            ChatMessage(
                role=role,
                content=content,
            )
        )

        self.conversations[conversation_id] = (
            self.conversations[conversation_id][-self.max_messages:]
        )

    def clear(self, conversation_id: str) -> None:
        self.conversations.pop(conversation_id, None)


conversation_memory = ConversationMemory()
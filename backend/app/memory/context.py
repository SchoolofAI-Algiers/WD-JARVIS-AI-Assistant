from collections.abc import Sequence

from app.models.chat import ChatMessage


class ContextBuilder:
    """Build a bounded, provider-neutral message context for one turn."""

    def __init__(self, max_messages: int = 20):
        if max_messages < 1:
            raise ValueError("max_messages must be at least 1")

        self.max_messages = max_messages

    def build(
        self,
        previous_messages: Sequence[ChatMessage],
        current_user_message: str,
    ) -> list[ChatMessage]:
        """Return chronological history plus the current user message.

        The returned list is new, so building context does not mutate memory.
        A matching final user message is treated as the current message already
        being present. The normal assistant flow supplies history from before
        the current turn, but this guard prevents accidental duplication.
        The maximum applies to the complete context, including the current turn.
        """
        context = list(previous_messages)

        current_message_is_present = (
            bool(context)
            and context[-1].role == "user"
            and context[-1].content == current_user_message
        )
        if not current_message_is_present:
            context.append(
                ChatMessage(role="user", content=current_user_message)
            )

        return context[-self.max_messages :]

from app.memory.conversation import conversation_memory


class Assistant:
    def process(
        self,
        conversation_id: str,
        message: str,
    ) -> dict:
        previous_messages = conversation_memory.get_messages(
            conversation_id
        )

        response = self._generate_response(
            message=message,
            previous_messages=previous_messages,
        )

        conversation_memory.add_message(
            conversation_id=conversation_id,
            role="user",
            content=message,
        )

        conversation_memory.add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=response,
        )

        return {
            "message": response,
            "metadata": {
                "type": "mock",
            },
        }

    def _generate_response(
        self,
        message: str,
        previous_messages: list,
    ) -> str:
        lower_message = message.lower().strip()

        if "what did i just say" in lower_message:
            if previous_messages:
                last_user_message = next(
                    (
                        item
                        for item in reversed(previous_messages)
                        if item.role == "user"
                    ),
                    None,
                )

                if last_user_message:
                    return (
                        f'You previously said: '
                        f'"{last_user_message.content}"'
                    )

            return "I don't have a previous message to refer to."

        if lower_message in {"hello", "hi", "hey"}:
            return "Hello. How can I assist you?"

        return f"JARVIS received: {message}"


assistant = Assistant()
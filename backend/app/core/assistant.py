from app.memory.conversation import conversation_memory
from app.tools.router import tool_router


class Assistant:
    def process(
        self,
        conversation_id: str,
        message: str,
    ) -> dict:
        previous_messages = conversation_memory.get_messages(
            conversation_id
        )

        tool_name = tool_router.detect_tool(message)

        if tool_name:
            try:
                tool_result = tool_router.execute(
                    tool_name=tool_name,
                    message=message,
                )

                response = self._format_tool_response(
                    tool_result
                )

                metadata = {
                    "type": "tool",
                    "tool": tool_result["tool"],
                }

            except Exception as error:
                response = (
                    f"I couldn't process that request: {error}"
                )

                metadata = {
                    "type": "error",
                    "tool": tool_name,
                }

        else:
            response = self._generate_response(
                message=message,
                previous_messages=previous_messages,
            )

            metadata = {
                "type": "mock",
            }

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
            "metadata": metadata,
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

    def _format_tool_response(
        self,
        tool_result: dict,
    ) -> str:
        if tool_result["tool"] == "calculator":
            expression = tool_result["expression"]
            result = tool_result["result"]

            if isinstance(result, float) and result.is_integer():
                result = int(result)

            return f"{expression} = {result}"

        if tool_result["tool"] == "datetime":
            datetime_result = tool_result["result"]

            return (
                f"Current UTC date: "
                f"{datetime_result['date']}. "
                f"Current UTC time: "
                f"{datetime_result['time']}."
            )

        return "The tool completed successfully."


assistant = Assistant()
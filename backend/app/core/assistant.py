from app.core.llm.client import LLMError
from app.core.llm.service import LLMService, llm_service
from app.memory.conversation import conversation_memory
from app.tools.router import tool_router
from app.tools.weather import weather_tool


class Assistant:
    def __init__(self, llm: LLMService | None = None):
        self.llm = llm or llm_service

    def process(
        self,
        conversation_id: str,
        message: str,
    ) -> dict:
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
            try:
                response = self.llm.generate_response(
                    conversation_id=conversation_id,
                    message=message,
                )
                metadata = {"type": "llm"}
            except LLMError as error:
                response = f"I couldn't generate a response: {error}"
                metadata = {"type": "error", "source": "llm"}

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

        if tool_result["tool"] == "weather":
            weather = tool_result["result"]

            description = weather_tool.describe_weather_code(
                weather["weather_code"]
            )

            return (
                f"Weather in {weather['city']}: "
                f"{description}, "
                f"{weather['temperature']}°C, "
                f"humidity {weather['humidity']}%, "
                f"wind {weather['wind_speed']} km/h."
            )

        if tool_result["tool"] == "reminders":
            result = tool_result["result"]
            if isinstance(result, list):
                if not result:
                    return "You have no pending reminders."
                lines = [f"You have {len(result)} pending reminder(s):"]
                for reminder in result:
                    due = f" (due {reminder['due_at'].replace('T', ' ')})" if reminder.get("due_at") else ""
                    lines.append(f"{reminder['id']}. {reminder['text']}{due}")
                return "\n".join(lines)
            if "completed" in result and "text" not in result:
                return "Reminder marked complete." if result["completed"] else "I couldn't find that reminder."
            due = f" for {result['due_at'].replace('T', ' ')}" if result.get("due_at") else ""
            return f"Reminder created{due}: {result['text']}"

        if tool_result["tool"] == "notes":
            result = tool_result["result"]
            if isinstance(result, list):
                if not result:
                    return "You don't have any notes yet."
                lines = [f"Your notes ({len(result)}):"]
                lines.extend(f"{note['id']}. {note['text']}" for note in result)
                return "\n".join(lines)
            return "Note saved."

        if tool_result["tool"] == "schedule":
            result = tool_result["result"]
            day = tool_result["date"]
            if not result:
                return f"You have no events scheduled for {day}."
            lines = [f"You have {len(result)} event(s) on {day}:"]
            lines.extend(f"{event['starts_at']} — {event['title']}" for event in result)
            return "\n".join(lines)

        if tool_result["tool"] == "workspace":
            result = tool_result["result"]
            if result["action"] == "application":
                app_names = {"notepad": "Notepad", "vs code": "VS Code", "chrome": "Chrome"}
                return f"{app_names[result['name']]} opened successfully."
            if result["action"] == "url":
                return f"Opened {result['url']}."
            return "Workspace opened."

        return "The tool completed successfully."


assistant = Assistant()

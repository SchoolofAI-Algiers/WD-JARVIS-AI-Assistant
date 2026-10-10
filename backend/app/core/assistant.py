import logging

from app.core.llm.client import LLMError
from app.core.llm.service import LLMService, llm_service
from app.memory.conversation import conversation_memory
from app.memory.context import ContextBuilder
from app.models.chat import ChatMessage
from app.rag.retriever import format_context, get_sources, retrieve
from app.tools.router import tool_router
from app.tools.weather import weather_tool

logger = logging.getLogger(__name__)


class Assistant:
    def __init__(self, llm: LLMService | None = None):
        self.llm = llm or llm_service
        self.context_builder = ContextBuilder(
            max_messages=conversation_memory.max_messages
        )

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
            context = self.context_builder.build(
                previous_messages=previous_messages,
                current_user_message=message,
            )

            chunks = self._search_knowledge(message)

            try:
                response = self.llm.generate_response(
                    conversation_id=conversation_id,
                    message=message,
                    retrieved_context=format_context(chunks) if chunks else "",
                )

                metadata = {"type": "rag", "sources": get_sources(chunks)} if chunks else {"type": "llm"}

            except LLMError:
                logger.exception("LLM call failed")
                response = self._generate_response(
                    context=context,
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

    def _search_knowledge(self, message: str) -> list:
        """Returns [] if nothing relevant (or if Weaviate is unreachable)."""
        try:
            return retrieve(message)
        except Exception:
            logger.exception("RAG search failed")
            return []

    def _generate_response(
        self,
        context: list[ChatMessage],
    ) -> str:
        message = context[-1].content
        lower_message = message.lower().strip()

        if "what did i just say" in lower_message:
            previous_context = context[:-1]
            if previous_context:
                last_user_message = next(
                    (
                        item
                        for item in reversed(previous_context)
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
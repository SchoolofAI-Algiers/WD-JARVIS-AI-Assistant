import re
from datetime import date, datetime, time, timedelta

from app.tools.calculator import calculator
from app.tools.datetime import datetime_tool
from app.tools.notes import notes_tool
from app.tools.reminders import reminder_tool
from app.tools.schedule import schedule_tool
from app.tools.weather import weather_tool
from app.tools.workspace import workspace_tool


class ToolRouter:
    def detect_tool(self, message: str) -> str | None:
        lower_message = message.lower()

        if re.search(r"\b(remind me|add (?:a )?task|show (?:my )?(?:tasks|reminders)|list (?:my )?(?:tasks|reminders)|complete (?:task|reminder)\s+#?\d+)\b", lower_message):
            return "reminders"
        if re.search(r"\b(take a note|save (?:this )?note|show (?:my )?notes|list (?:my )?notes|search (?:my )?notes)\b", lower_message):
            return "notes"
        if re.search(r"\b(add|schedule|show|check) (?:a )?(?:meeting|event|appointment|schedule)|\bwhat do i have (?:today|tomorrow)|\bshow my schedule\b", lower_message):
            return "schedule"
        if re.search(r"\b(open (?:the )?(?:workspace|project|folder)|prepare my workspace|open (?:notepad|vs code|chrome))\b|\bhttps?://", lower_message):
            return "workspace"

        calculator_keywords = [
            "calculate",
            "what is",
            "what's",
            "solve",
            "multiply",
            "times",
            "plus",
            "minus",
            "divided by",
        ]

        if (
            any(
                keyword in lower_message
                for keyword in calculator_keywords
            )
            and any(char.isdigit() for char in message)
        ):
            return "calculator"

        if (
            any(
                operator in message
                for operator in [
                    "+",
                    "-",
                    "*",
                    "×",
                    "/",
                    "÷",
                    "%",
                ]
            )
            and any(char.isdigit() for char in message)
        ):
            return "calculator"

        datetime_keywords = [
            "what time is it",
            "what's the time",
            "what is the time",
            "current time",
            "current date",
            "what date is it",
            "what's today's date",
            "today's date",
        ]

        if any(
            keyword in lower_message
            for keyword in datetime_keywords
        ):
            return "datetime"

        weather_keywords = [
            "weather",
            "temperature",
            "forecast",
            "rain",
            "sunny",
            "cloudy",
        ]

        if any(
            keyword in lower_message
            for keyword in weather_keywords
        ):
            return "weather"

        return None

    def execute(
        self,
        tool_name: str,
        message: str,
    ) -> dict:
        if tool_name == "calculator":
            expression = self._extract_expression(message)

            result = calculator.calculate(expression)

            return {
                "tool": "calculator",
                "result": result,
                "expression": expression,
            }

        if tool_name == "datetime":
            result = datetime_tool.get_current_datetime()

            return {
                "tool": "datetime",
                "result": result,
            }

        if tool_name == "weather":
            city = self._extract_city(message)

            result = weather_tool.get_weather(city)

            return {
                "tool": "weather",
                "result": result,
            }

        if tool_name == "reminders":
            complete = re.search(r"\bcomplete (?:task|reminder)\s+#?(\d+)\b", message, re.I)
            if complete:
                reminder_id = int(complete.group(1))
                result = {"id": reminder_id, "completed": reminder_tool.complete_reminder(reminder_id)}
            elif re.search(r"\b(show|list)\b", message, re.I):
                result = reminder_tool.list_reminders()
            else:
                body = re.sub(r"^\s*(?:remind me|add (?:a )?task\s*:?)\s*", "", message, flags=re.I).strip()
                due_at, body = self._extract_due(body)
                result = reminder_tool.create_reminder(body, due_at)
            return {"tool": "reminders", "result": result}

        if tool_name == "notes":
            if re.search(r"\b(search)\b", message, re.I):
                query = re.sub(r"^.*?\bnotes?\s+(?:for|about)\s+", "", message, flags=re.I).strip(" ?.")
                result = notes_tool.search_notes(query)
            elif re.search(r"\b(show|list)\b", message, re.I):
                result = notes_tool.list_notes()
            else:
                body = re.sub(r"^\s*(?:take a note|save (?:this )?note)\s*:?\s*", "", message, flags=re.I).strip()
                result = notes_tool.create_note(body)
            return {"tool": "notes", "result": result}

        if tool_name == "schedule":
            target_day = date.today()
            if "tomorrow" in message.lower():
                target_day += timedelta(days=1)
            elif re.search(r"\btoday\b", message, re.I):
                pass
            elif re.search(r"\b\d{4}-\d{2}-\d{2}\b", message):
                target_day = date.fromisoformat(re.search(r"\b\d{4}-\d{2}-\d{2}\b", message).group())
            if re.search(r"\b(add|schedule)\b", message, re.I):
                title = re.sub(r"^.*?\b(?:meeting|event|appointment)\s*", "", message, flags=re.I).strip(" :")
                title = re.sub(r"\b(?:today|tomorrow)\b.*$", "", title, flags=re.I).strip()
                title = re.sub(r"\bat\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?\b.*$", "", title, flags=re.I).strip()
                if not title:
                    title = "Meeting"
                hourmatch = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", message, re.I)
                if not hourmatch:
                    raise ValueError("Please include an event time.")
                hour, minute = int(hourmatch.group(1)), int(hourmatch.group(2) or 0)
                if hourmatch.group(3) and hourmatch.group(3).lower() == "pm" and hour < 12: hour += 12
                if hourmatch.group(3) and hourmatch.group(3).lower() == "am" and hour == 12: hour = 0
                result = schedule_tool.create_event(title, datetime.combine(target_day, time(hour, minute)).isoformat())
            else:
                result = schedule_tool.list_events(target_day.isoformat())
            return {"tool": "schedule", "result": result, "date": target_day.isoformat()}

        if tool_name == "workspace":
            url = re.search(r"https?://\S+", message)
            if url:
                result = workspace_tool.open_url(url.group().rstrip(".,!?"))
            elif re.search(r"\b(open|launch)\s+(?:the\s+)?(notepad|vs code|chrome)\b", message, re.I):
                app = re.search(r"\b(notepad|vs code|chrome)\b", message, re.I).group(1)
                result = workspace_tool.open_application(app)
            else:
                path = re.sub(r"^.*?\b(?:workspace|project|folder)\s*", "", message, flags=re.I).strip(" :") or "."
                result = workspace_tool.open_workspace(path)
            return {"tool": "workspace", "result": result}

        raise ValueError(
            f"Unknown tool: {tool_name}"
        )

    def _extract_due(self, text: str) -> tuple[str | None, str]:
        match = re.search(r"\b(today|tomorrow)\s+at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", text, re.I)
        if not match:
            match = re.search(r"\bat\s+(\d{1,2}):(\d{2})\b", text)
            if match:
                hour, minute = int(match.group(1)), int(match.group(2))
                due = datetime.combine(date.today(), time(hour, minute))
                return due.isoformat(timespec="minutes"), (text[:match.start()] + text[match.end():]).strip(" :")
            return None, text
        day = date.today() + (timedelta(days=1) if match.group(1).lower() == "tomorrow" else timedelta())
        hour, minute = int(match.group(2)), int(match.group(3) or 0)
        suffix = (match.group(4) or "").lower()
        if suffix == "pm" and hour < 12: hour += 12
        if suffix == "am" and hour == 12: hour = 0
        due = datetime.combine(day, time(hour, minute))
        return due.isoformat(timespec="minutes"), (text[:match.start()] + text[match.end():]).strip(" :")

    def _extract_expression(self, message: str) -> str:
        expression = message.lower()

        prefixes = [
            "calculate",
            "what is",
            "what's",
            "solve",
        ]

        for prefix in prefixes:
            expression = expression.replace(
                prefix,
                "",
                1,
            )

        expression = (
            expression
            .replace("multiply", "*")
            .replace("times", "*")
            .replace("plus", "+")
            .replace("minus", "-")
            .replace("divided by", "/")
            .replace("×", "*")
            .replace("÷", "/")
        )

        allowed_characters = "0123456789.+-*/%() "

        expression = "".join(
            character
            for character in expression
            if character in allowed_characters
        )

        return expression.strip()

    def _extract_city(self, message: str) -> str:
        lower_message = message.lower().strip()

        prefixes = [
            "what's the weather in ",
            "what is the weather in ",
            "weather in ",
            "temperature in ",
            "forecast in ",
        ]

        for prefix in prefixes:
            if lower_message.startswith(prefix):
                return message[len(prefix):].strip()

        return "Algiers"


tool_router = ToolRouter()

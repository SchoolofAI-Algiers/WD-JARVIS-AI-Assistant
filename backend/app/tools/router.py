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

        if re.search(
            r"\b(?:remind me|set (?:a )?reminder|add (?:a )?task|"
            r"show (?:my |pending )?(?:tasks|reminders)|list (?:my |pending )?(?:tasks|reminders)|"
            r"complete (?:task|reminder)\s+#?\d+)\b",
            lower_message,
        ):
            return "reminders"
        if re.search(
            r"\b(?:take a note|save (?:this )?note|show (?:my )?notes|"
            r"list (?:my )?notes|search (?:my )?notes)\b",
            lower_message,
        ):
            return "notes"
        if re.search(
            r"\bwhat do i have (?:today|tomorrow)\b|"
            r"\b(?:show|check|list) (?:my |today's |tomorrow's )?schedule\b|"
            r"\b(?:today's|tomorrow's) schedule\b",
            lower_message,
        ):
            return "schedule"
        if re.search(
            r"^\s*(?:add|schedule)\s+(?:(?:a|an)\s+)?(?:meeting|event|appointment)\b|"
            r"^\s*schedule\s+(?!my\s+schedule\b)\S",
            lower_message,
        ):
            return "schedule"
        if re.search(
            r"\b(?:open|launch) (?:the )?(?:workspace|project|folder)\b|"
            r"\bprepare my workspace\b|"
            r"\b(?:open|launch) (?:notepad|vs code|chrome)\b|"
            r"\b(?:open|visit) (?:this )?https?://\S+",
            lower_message,
        ):
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
                body = re.sub(
                    r"^\s*(?:remind me|set (?:a )?reminder|add (?:a )?task)\s*:?\s*",
                    "",
                    message,
                    flags=re.I,
                ).strip()
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
            target_day = self._extract_schedule_day(message)
            if re.search(r"^\s*(?:add|schedule)\b", message, re.I):
                time_match = self._find_time(message)
                if not time_match:
                    raise ValueError("Please include an event time, such as 'at 3 PM'.")
                event_time = self._parse_time(time_match)
                title = self._extract_event_title(message)
                result = schedule_tool.create_event(
                    title,
                    datetime.combine(target_day, event_time).isoformat(timespec="minutes"),
                )
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
        time_match = self._find_time(text)
        if not time_match:
            return None, text

        day_match = re.search(r"\b(today|tomorrow)\b", text, re.I)
        due_day = date.today()
        if day_match and day_match.group(1).lower() == "tomorrow":
            due_day += timedelta(days=1)

        due_at = datetime.combine(due_day, self._parse_time(time_match))
        removal_start = min(time_match.start(), day_match.start()) if day_match else time_match.start()
        removal_end = max(time_match.end(), day_match.end()) if day_match else time_match.end()
        task_text = (text[:removal_start] + text[removal_end:]).strip(" \t,.:;-")
        return due_at.isoformat(timespec="minutes"), task_text

    def _find_time(self, text: str) -> re.Match | None:
        return re.search(r"\bat\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", text, re.I)

    def _parse_time(self, match: re.Match) -> time:
        hour = int(match.group(1))
        minute = int(match.group(2) or 0)
        suffix = (match.group(3) or "").lower()
        if not 0 <= minute <= 59:
            raise ValueError("Please provide a valid time with minutes from 00 to 59.")
        if suffix:
            if not 1 <= hour <= 12:
                raise ValueError("Please provide a valid 12-hour time.")
            if suffix == "pm" and hour < 12:
                hour += 12
            elif suffix == "am" and hour == 12:
                hour = 0
        elif not 0 <= hour <= 23:
            raise ValueError("Please provide a valid 24-hour time.")
        return time(hour, minute)

    def _extract_schedule_day(self, message: str) -> date:
        lower_message = message.lower()
        if re.search(r"\btomorrow\b", lower_message):
            return date.today() + timedelta(days=1)
        if re.search(r"\btoday\b", lower_message):
            return date.today()
        day_match = re.search(r"\b\d{4}-\d{2}-\d{2}\b", message)
        if day_match:
            try:
                return date.fromisoformat(day_match.group())
            except ValueError as error:
                raise ValueError("Please provide a valid event date in YYYY-MM-DD format.") from error
        return date.today()

    def _extract_event_title(self, message: str) -> str:
        event_type = re.search(r"\b(meeting|event|appointment)\b", message, re.I)
        if event_type:
            title = message[event_type.end():]
        else:
            title = re.sub(r"^\s*schedule\s+", "", message, flags=re.I)

        time_match = self._find_time(title)
        if time_match:
            title = title[:time_match.start()] + title[time_match.end():]
        title = re.sub(r"\b(?:on\s+)?\d{4}-\d{2}-\d{2}\b|\b(?:today|tomorrow)\b", "", title, flags=re.I)
        title = title.strip(" \t,.:;-")
        if title.lower() in {"for", "on"}:
            title = ""
        if title:
            return title
        if event_type:
            return event_type.group(1).capitalize()
        raise ValueError("Please include an event title.")

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

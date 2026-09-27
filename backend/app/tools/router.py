from app.tools.calculator import calculator
from app.tools.datetime import datetime_tool


class ToolRouter:
    def detect_tool(self, message: str) -> str | None:
        lower_message = message.lower()

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

        raise ValueError(
            f"Unknown tool: {tool_name}"
        )

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


tool_router = ToolRouter()
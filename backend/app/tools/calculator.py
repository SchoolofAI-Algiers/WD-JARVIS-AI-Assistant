import ast
import operator


class CalculatorError(Exception):
    pass


class Calculator:
    OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    def calculate(self, expression: str) -> float | int:
        expression = (
            expression
            .replace("×", "*")
            .replace("÷", "/")
        )

        try:
            tree = ast.parse(
                expression,
                mode="eval",
            )
        except SyntaxError as error:
            raise CalculatorError(
                "Invalid mathematical expression."
            ) from error

        try:
            result = self._evaluate(tree.body)
        except (TypeError, ZeroDivisionError, OverflowError) as error:
            raise CalculatorError(
                "Could not calculate the expression."
            ) from error

        return result

    def _evaluate(self, node: ast.AST) -> float | int:
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value

            raise CalculatorError(
                "Only numbers are supported."
            )

        if isinstance(node, ast.BinOp):
            operator_function = self.OPERATORS.get(
                type(node.op)
            )

            if operator_function is None:
                raise CalculatorError(
                    "Unsupported operator."
                )

            left = self._evaluate(node.left)
            right = self._evaluate(node.right)

            return operator_function(left, right)

        if isinstance(node, ast.UnaryOp):
            operator_function = self.OPERATORS.get(
                type(node.op)
            )

            if operator_function is None:
                raise CalculatorError(
                    "Unsupported operator."
                )

            operand = self._evaluate(node.operand)

            return operator_function(operand)

        raise CalculatorError(
            "Unsupported expression."
        )


calculator = Calculator()
import ast
import operator

# Only these operators are allowed — this is what makes it "sandboxed"
# instead of a raw eval() that could execute arbitrary code.
_ALLOWED_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
}


def _eval_node(node):
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError("Only numeric constants are allowed")
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_OPS:
        return _ALLOWED_OPS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_OPS:
        return _ALLOWED_OPS[type(node.op)](_eval_node(node.operand))
    raise ValueError(f"Disallowed expression: {ast.dump(node)}")


def calculator(expression: str) -> dict:
    """Evaluates basic arithmetic ONLY — no function calls, no attribute
    access, no imports. This is the actual engineering answer to 'never use
    raw eval()': parse to an AST and explicitly whitelist what's allowed."""
    try:
        tree = ast.parse(expression, mode="eval")
        result = _eval_node(tree.body)
        return {"result": result}
    except Exception as e:
        return {"error": f"Could not evaluate: {e}"}
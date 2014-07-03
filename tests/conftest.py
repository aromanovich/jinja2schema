from jinja2schema.model import Variable
import difflib

def pytest_assertrepr_compare(op, left, right):
    if isinstance(left, Variable) and isinstance(right, Variable) and op == '==':
        left = str(left).split('\n')
        right = str(right).split('\n')
        return (
            ['comparing two structures'] +
            left +
            ['-' * 45] +
            right +
            ['diff:'] +
            list(difflib.unified_diff(left, right))
        )
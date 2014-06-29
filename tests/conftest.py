from jinja2schema.model import Variable


def pytest_assertrepr_compare(op, left, right):
    if isinstance(left, Variable) and isinstance(right, Variable) and op == '==':
        return (
            ['comparing two structures'] +
            str(left).split('\n') +
            ['-' * 45] +
            str(right).split('\n')
        )
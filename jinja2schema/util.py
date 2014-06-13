import colorama
from jinja2 import nodes


def visualize(ast, level=0):
    def print_(s, color=''):
        print color + '  ' * level + s + colorama.Fore.RESET

    if isinstance(ast, nodes.Node):
        print_(ast.__class__.__name__, color=colorama.Fore.RED)
        for name, field in ast.iter_fields():
            print_(name)
            if isinstance(field, list):
                for n in field:
                    visualize(n, level=level+1)
            elif ast is not None:
                visualize(field, level=level+1)
    else:
        print_(repr(ast), color=colorama.Fore.GREEN)
    return

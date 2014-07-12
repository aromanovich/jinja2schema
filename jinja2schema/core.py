"""
There are two types of visitors, expression and statement.

Expression visitors return tuple which contains expression type and expression structure.

Statement visitors return :class:`.models.Dictionary` which contains
structures of variables used within the statement.
"""
import jinja2

from .visitors import visit_many
from .model import Scalar, Dictionary


def _post_process(var):
    if isinstance(var, Dictionary):
        for k, v in var.items():
            if v.constant and not v.may_be_defined:
                del var[k]
            else:
                _post_process(v)
    return var


def infer_from_ast(ast):
    """
    :type ast: :class:`nodes.Template`
    """
    rv = visit_many(ast.body, Scalar)
    return _post_process(rv)


def parse(template, jinja2_env=None):
    """
    :type template: basestring
    :type jinja2_env: :class:`jinja2.Environment`
    :rtype: :class:`nodes.Template`
    """
    if jinja2_env is None:
        jinja2_env = jinja2.Environment()
    return jinja2_env.parse(template)


def infer(template):
    """Returns a :class:`Dictionary` that describes a structure of a context required by ``template``.

    :type template: basestring
    :rtype: class:`Dictionary`
    """
    return infer_from_ast(parse(template))

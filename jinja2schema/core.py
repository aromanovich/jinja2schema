# coding: utf-8
"""
jinja2schema.core
~~~~~~~~~~~~~~~~~
"""
import jinja2

from .config import Config
from .model import Dictionary
from .visitors import visit
from . import _compat


def parse(template, jinja2_env=None):
    """Parses Jinja2 template and returns it's AST.

    :type template: basestring
    :type jinja2_env: :class:`jinja2.Environment`
    :rtype: :class:`jinja2.nodes.Template`
    """
    if jinja2_env is None:
        jinja2_env = jinja2.Environment()
    return jinja2_env.parse(template)


def _ignore_constants(var):
    if isinstance(var, Dictionary):
        for k, v in list(_compat.iteritems(var)):
            if v.constant and not v.may_be_defined:
                del var[k]
            else:
                _ignore_constants(v)
    return var


def infer_from_ast(ast, ignore_constants=True, config=Config()):
    """Returns a :class:`.model.Dictionary` which reflects a structure of variables used
    within ``ast``.

    :param ast: AST
    :type ast: :class:`jinja2.nodes.Node`
    :param ignore_constants: excludes constant variables from a resulting structure
    :param config: a config
    :type config: :class:`.config.Config`
    :rtype: :class:`.model.Dictionary`
    :raises: :class:`.exceptions.MergeException`, :class:`.exceptions.InvalidExpression`,
             :class:`.exceptions.UnexpectedExpression`
    """
    rv = visit(ast, config)
    if ignore_constants:
        rv = _ignore_constants(rv)
    return rv


def infer(template, config=Config()):
    """Returns a :class:`.model.Dictionary` which reflects a structure of the context required by ``template``.

    :param template: a template
    :type template: string
    :param config: a config
    :type config: :class:`.config.Config`
    :rtype: :class:`.model.Dictionary`
    :raises: :class:`.exceptions.MergeException`, :class:`.exceptions.InvalidExpression`,
             :class:`.exceptions.UnexpectedExpression`
    """
    return infer_from_ast(parse(template), config=config, ignore_constants=True)

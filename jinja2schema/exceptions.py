# coding: utf-8
"""
jinja2schema.exceptions
~~~~~~~~~~~~~~~~~~~~~~~
"""
from jinja2schema.model import Scalar


class InferException(Exception):
    """Base class for jinja2schema exceptions."""


class MergeException(InferException):
    """Conflict of merging two structures.

    .. attribute:: fst

        :class:`Variable`

    .. attribute:: snd

        :class:`Variable`
    """
    def __init__(self, fst, snd):
        self.fst = fst
        self.snd = snd

    def __str__(self):
        get_label = lambda s: 'unnamed variable' if s.label is None else 'variable "{}"'.format(s.label)
        def get_usage(s):
            rv = s.__class__.__name__.lower()
            if isinstance(s, Scalar):
                rv += ' ({})'.format(', '.join(s.possible_types))
            return rv
        get_linenos = lambda s: ', '.join(map(str, s.linenos))
        return ('{fst_label} (used as {fst_usage} on lines {fst_linenos}) conflicts with '
                '{snd_label} (used as {snd_usage} on lines: {snd_linenos})').format(
                    fst_label=get_label(self.fst), snd_label=get_label(self.snd),
                    fst_usage=get_usage(self.fst), snd_usage=get_usage(self.snd),
                    fst_linenos=get_linenos(self.fst), snd_linenos=get_linenos(self.snd))


class UnexpectedExpression(InferException):
    """Raised when a visitor was expecting compatibility with :attr:`expected_struct`,
    but got :attr:`actual_ast` of structure :attr:`actual_struct`.

    Compatibility is checked by merging expected structure with actual one.

    .. attribute:: expected_struct

        expected :class:`.model.Variable`

    .. attribute:: actual_ast

        actual :class:`jinja2.nodes.Node`

    .. attribute:: actual_ast

        :class:`.model.Variable` described by ``actual_ast``
    """
    def __init__(self, expected_struct, actual_ast, actual_struct):
        self.expected_struct = expected_struct
        self.actual_ast = actual_ast
        self.actual_struct = actual_struct

    def __str__(self):
        return ('conflict on the line {lineno}\n'
                'got: AST node jinja2.nodes.{node} of structure {actual_struct}\n'
                'expected structure: {expected_struct}').format(
                    lineno=self.actual_ast.lineno,
                    node=self.actual_ast.__class__.__name__,
                    actual_struct=self.actual_struct,
                    expected_struct=self.expected_struct)


class InvalidExpression(InferException):
    """Raised when a template uses Jinja2 features that are not supported by the library
    or when a template contains incorrect expressions (i.e., such as applying ``divisibleby`` filter
    without an argument).

    .. attribute:: ast

        :class:`jinja2.nodes.Node` caused the exception
    """
    def __init__(self, ast, message):
        self.ast = ast
        self.message = message

    def __str__(self):
        return 'line {}: {}'.format(self.ast.lineno, self.message)
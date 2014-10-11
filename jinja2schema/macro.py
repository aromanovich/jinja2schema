# coding: utf-8
"""
jinja2schema.macro
~~~~~~~~~~~~~~~~~~
"""
from . import _compat
from .config import default_config
from .mergers import merge
from .model import Unknown, Dictionary


class Macro(object):
    """A macro.

    .. attribute:: name

        Name.

    .. attribute:: args

        Positional arguments. A list of 2-tuples whose first element is string that
        contains argument name and second is a :class:`Variable` -- a structure which
        expected of that argument.
        Arguments must be in the same order as they are listed in macro signature.

    .. attribute:: kwargs

        The same as :attr:`args`, but keyword arguments.
    """
    def __init__(self, name, args, kwargs):
        self.name = name
        self.args = args
        self.kwargs = kwargs


class MacroCall(object):
    def __init__(self, macro, passed_args, passed_kwargs, config=default_config):
        self.config = config

        self.passed_args = []
        for arg_ast in passed_args:
            arg_rtype, arg_struct = visit_expr(
                arg_ast, Context(predicted_struct=Unknown.from_ast(arg_ast)), config=config)
            self.passed_args.append((arg_ast, arg_rtype))

        self.passed_kwargs = {}
        for kwarg_ast in passed_kwargs:
            kwarg_rtype, kwarg_struct = visit_expr(
                kwarg_ast.value, Context(predicted_struct=Unknown.from_ast(kwarg_ast)), config=config)
            self.passed_kwargs[kwarg_ast.key] = (kwarg_ast, kwarg_rtype)

        self.expected_args = macro.args[:]
        self.expected_kwargs = macro.kwargs[:]

    def _match_passed_args(self, to_args):
        rv = Dictionary()
        matched_args = list(zip(self.passed_args, to_args))
        for i, ((arg_ast, arg), (expected_arg_name, expected_arg)) in enumerate(matched_args, start=1):
            _, s = visit_expr(arg_ast, Context(predicted_struct=merge(arg, expected_arg)), config=self.config)
            rv = merge(rv, s)
        del self.passed_args[:len(matched_args)]
        del to_args[:len(matched_args)]
        return rv

    def match_passed_args_to_expected_args(self):
        return self._match_passed_args(self.expected_args)

    def match_passed_args_to_expected_kwargs(self):
        return self._match_passed_args(self.expected_kwargs)

    def _match_passed_kwargs(self, to_args):
        rv = Dictionary()
        for kwarg_name, (kwarg_ast, kwarg_type) in list(_compat.iteritems(self.passed_kwargs)):
            for (expected_arg_name, expected_arg_struct) in list(to_args):
                if kwarg_name == expected_arg_name:
                    _, s = visit_expr(kwarg_ast.value,
                                      Context(predicted_struct=merge(kwarg_type, expected_arg_struct)),
                                      config=self.config)
                    rv = merge(rv, s)
                    to_args.remove((expected_arg_name, expected_arg_struct))
                    del self.passed_kwargs[kwarg_name]
        return rv

    def match_passed_kwargs_to_expected_args(self):
        return self._match_passed_kwargs(self.expected_args)

    def match_passed_kwargs_to_expected_kwargs(self):
        return self._match_passed_kwargs(self.expected_kwargs)


from .visitors.expr import visit_expr
from .visitors.expr import Context

# coding: utf-8
"""

jinja2schema
============

Type inference for Jinja2 templates.

See http://jinja2schema.rtfd.org/ for documentation.

:copyright: (c) 2014 Anton Romanovich
:license: BSD

"""

__title__ = 'jinja2schema'
__author__ = 'Anton Romanovich'
__license__ = 'BSD'
__copyright__ = 'Copyright 2014 Anton Romanovich'
__version__ = '0.0.2'
__version_info__ = tuple(int(i) for i in __version__.split('.'))


from .core import parse, infer, infer_from_ast
from .exceptions import InferException, MergeException, InvalidExpression, UnexpectedExpression

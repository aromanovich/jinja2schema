# coding: utf-8
"""
jinja2schema.core
~~~~~~~~~~~~~~~~~
"""
import jinja2

from .config import Config
from .model import Dictionary, List, Tuple, Scalar, Number, Unknown, Boolean, String
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
    rv = visit(ast, {}, config)
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


class JSONSchemaDraft4Encoder(object):
    """Extensible JSON schema encoder for :class:`.model.Variable`."""

    def encode_common_attrs(self, var):
        """Returns a subset of JSON schema of variable `var` that describes
        attributes that are common for all the variable types, such as label.
        """
        rv = {}
        if var.label:
            rv['title'] = var.label
        if var.value and var.used_with_default:
            rv['default'] = var.value
        return rv

    def encode(self, var):
        """Returns a JSON schema of variable `var`.

        :type var: :class:`.model.Variable`
        :rtype: :class:`dict`
        """
        rv = self.encode_common_attrs(var)
        if isinstance(var, Dictionary):
            rv.update({
                'type': 'object',
                'properties': dict((k, self.encode(v)) for k, v in var.iteritems()),
                'required': [k for k, v in var.iteritems() if v.required],
            })
        elif isinstance(var, List):
            rv.update({
                'type': 'array',
                'items': self.encode(var.item),
            })
        elif isinstance(var, Tuple):
            rv.update({
                'type': 'array',
                'items': [self.encode(item) for item in var.items],
            })
        elif isinstance(var, Unknown):
            rv['anyOf'] = [
                {'type': 'object'},
                {'type': 'array'},
                {'type': 'string'},
                {'type': 'number'},
                {'type': 'boolean'},
                {'type': 'null'},
            ]
        elif isinstance(var, String):
            rv['type'] = 'string'
        elif isinstance(var, Number):
            rv['type'] = 'number'
        elif isinstance(var, Boolean):
            rv['type'] = 'boolean'
        elif isinstance(var, Scalar):
            rv['anyOf'] = [
                {'type': 'boolean'},
                {'type': 'null'},
                {'type': 'number'},
                {'type': 'string'},
            ]
        return rv


class StringJSONSchemaDraft4Encoder(JSONSchemaDraft4Encoder):
    """Encodes :class:`.model.Unknown` and :class:`.model.Scalar` (but not it's subclasses --
    :class:`.model.String`, :class:`.model.Number` or :class:`.model.Boolean`) variables as strings.

    Useful for rendering forms using resulting JSON schema, as most of form-rendering
    tools do not support "anyOf" validator.
    """
    def encode(self, var):
        if isinstance(var, Unknown) or type(var) is Scalar:
            rv = self.encode_common_attrs(var)
            rv['type'] = 'string'
        else:
            rv = super(StringJSONSchemaDraft4Encoder, self).encode(var)
        return rv


def to_json_schema(var, jsonschema_encoder=JSONSchemaDraft4Encoder):
    """Returns JSON schema that describes ``var``.

    :param var: a variable
    :type var: :class:`.model.Variable`
    :param jsonschema_encoder: JSON schema encoder
    :type jsonschema_encoder: subclass of :class:`JSONSchemaEncoder`
    :return: :class:`dict`
    """
    return jsonschema_encoder().encode(var)

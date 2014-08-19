# coding: utf-8
"""
jinja2schema.config
~~~~~~~~~~~~~~~~~~~
"""
class Config(object):
    """Configuration."""

    TYPE_OF_VARIABLE_INDEXED_WITH_VARIABLE_TYPE = 'dictionary'
    """Possible values: ``"dictionary"`` or ``"list""``.

    For example, in the expression ``xs[a]`` variable ``xs`` may be a list as well as a dictionary.
    This setting is used to choose between a dictionary and a list when the variable is
    being indexed with another variable.
    """

    TYPE_OF_VARIABLE_INDEXED_WITH_INTEGER_TYPE = 'list'
    """Possible values: ``"dictionary"`` or ``"list""``.

    For example, in the expression ``xs[2]`` variable ``xs`` may be a list as well as a dictionary.
    This setting is used to choose between a dictionary and a list when the variable is
    being indexed with an integer.
    """

    ALLOW_ONLY_BOOLEAN_VARIABLES_IN_TEST = False
    """Whether or not to consider conditions in ``if`` statements as boolean.

    If this variable is not set, ``xs`` variable in template ``{% if xs %}{% endif %}`` will have
    unknown structure. If this variable is set, ``xs`` will be a boolean.
    """

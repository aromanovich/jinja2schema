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
    """Possible values: ``"dictionary"``, ``"list"`` or ``"tuple"``.

    For example, in the expression ``xs[2]`` variable ``xs`` may be a list as well as a dictionary or a tuple.
    This setting is used to choose between a dictionary, a tuple and a list when the variable is
    being indexed with an integer.
    """

    BOOLEAN_CONDITIONS = False
    """Whether or not to consider conditions in ``if`` statements as boolean.

    If this variable is not set, ``xs`` variable in template ``{% if xs %}{% endif %}`` will have
    unknown structure. If this variable is set, ``xs`` will be a boolean.
    """

    PACKAGE_NAME = ''
    """Name of the package where you want to load templates from.

    This configuration is for if you are using includes in your jinja templates. This tells jinja
    where to look to be able to load the included template from. If you do not plan on using ``includes``
    this configuration is not needed.
    """

    TEMPLATE_DIR = 'templates'
    """Name of the directory where you want to load templates from. Defaulted to ``templates``

    This configuration is for if you are using includes in your jinja templates. This tells jinja
    which directoy to look to be able to load the included template from. If you do not plan on using ``includes``
    this configuration is not needed.
    """

    def __init__(self,
                 TYPE_OF_VARIABLE_INDEXED_WITH_VARIABLE_TYPE='dictionary',
                 TYPE_OF_VARIABLE_INDEXED_WITH_INTEGER_TYPE='list',
                 BOOLEAN_CONDITIONS=False,
                 PACKAGE_NAME='',
                 TEMPLATE_DIR='templates'):
        if TYPE_OF_VARIABLE_INDEXED_WITH_VARIABLE_TYPE not in ('dictionary', 'list'):
            raise ValueError('TYPE_OF_VARIABLE_INDEXED_WITH_VARIABLE_TYPE must be'
                             'either "dictionary" or "list"')
        if TYPE_OF_VARIABLE_INDEXED_WITH_INTEGER_TYPE not in ('dictionary', 'list', 'tuple'):
            raise ValueError('TYPE_OF_VARIABLE_INDEXED_WITH_VARIABLE_TYPE must be'
                             'either "dictionary", "tuple" or "list"')
        self.TYPE_OF_VARIABLE_INDEXED_WITH_INTEGER_TYPE = TYPE_OF_VARIABLE_INDEXED_WITH_INTEGER_TYPE
        self.TYPE_OF_VARIABLE_INDEXED_WITH_VARIABLE_TYPE = TYPE_OF_VARIABLE_INDEXED_WITH_VARIABLE_TYPE
        self.BOOLEAN_CONDITIONS = BOOLEAN_CONDITIONS
        self.PACKAGE_NAME = PACKAGE_NAME
        self.TEMPLATE_DIR = TEMPLATE_DIR


default_config = Config()

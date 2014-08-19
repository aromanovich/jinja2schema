class Config(object):
    VARIABLE_INDEXED_WITH_VARIABLE_TYPE = 'dictionary'
    """Possible values: ``"dictionary"`` or ``"list""``.

    For example, in the expression ``xs[a]`` variable ``xs`` may be a list as well as a dictionary.
    This setting is used to choose between a dictionary and a list when the variable is
    being indexed with another variable.
    """

    VARIABLE_INDEXED_WITH_INTEGER_TYPE = 'list'
    """Possible values: ``"dictionary"`` or ``"list""``.

    For example, in the expression ``xs[2]`` variable ``xs`` may be a list as well as a dictionary.
    This setting is used to choose between a dictionary and a list when the variable is
    being indexed with an integer.
    """

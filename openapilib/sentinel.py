import logging

_log = logging.getLogger(__name__)


class Sentinel:
    """
    A class to be used as a canary value instead of the commonly used.
    Use this where you would sometimes otherwise use ``NAME = object()``, as in

    >>> DEFAULT = object()
    >>> data = {'foo': None}
    >>> def get(key, default=DEFAULT):
    ...     try:
    ...         data[key]
    ...     except KeyError as exc:
    ...         if default is not DEFAULT:
    ...             return default
    ...         else:
    ...             raise exc

    This class has the advantage of the "name" property, which will get
    printed when calling :any:`repr`\ (sentinel_instance).

    >>> DEFAULT = Sentinel('DEFAULT')
    >>> repr(DEFAULT)
    'DEFAULT'
    """
    def __init__(self, name, doc=None):
        _log.debug('Creating Sentinel, name=%r, doc=%r', name, doc)
        self.name = name
        if self.__doc__ is not None:
            self.__doc__ = doc

    def __repr__(self):
        return self.name

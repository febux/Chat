"""
Singleton pattern implementation in Python
"""

from functools import wraps


class Singleton(object):
    """
    Singleton class implementation using the Singleton pattern.
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance


class SingletonMeta(type):
    """
    Singleton class decorator
    """

    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(SingletonMeta, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


def singleton_func(func):
    """
    Singleton function decorator
    """

    @wraps(func)
    def wrapped(*args, **kwargs):
        if not wrapped.__result:  # type: ignore[assignment]
            wrapped.__result = func(*args, **kwargs)  # type: ignore[assignment]
        return wrapped.__result  # type: ignore[assignment]

    wrapped.__result = None  # type: ignore[assignment]
    return wrapped


def singleton_cls(class_):
    """
    Singleton class decorator
    """

    class class_w(class_):
        """
        Private constructor for the singleton class
        """

        _instance = None

        def __new__(cls, *args, **kwargs):
            if class_w._instance is None:
                class_w._instance = super(class_w, cls).__new__(cls, *args, **kwargs)
                class_w._instance._sealed = False
            return class_w._instance

        def __init__(self, *args, **kwargs):
            if self._sealed:
                return
            super(class_w, self).__init__(*args, **kwargs)
            self._sealed = True

    class_w.__name__ = class_.__name__
    return class_w

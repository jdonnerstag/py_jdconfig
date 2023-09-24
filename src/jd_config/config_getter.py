#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Assuming a deep Mapping- and Sequence-like structure, walk along
a path and support dict-like get(), set() and delete() operations
and the elements.
"""

import logging
from typing import Any, Iterable, Mapping, Tuple, Type, Sequence

__parent__name__ = __name__.rpartition('.')[0]
logger = logging.getLogger(__parent__name__)


class ConfigException(Exception):
    """Base class for Config Exceptions"""

DEFAULT = object()

PathType: Type = str | int | Iterable

WalkResultType: Type = Tuple[Tuple[Mapping, str] | Tuple[Sequence, int]]

class ConfigGetter:
    """Dict-like get, set and delete operations on deep Mapping- and Sequence-like structures.
    """

    @classmethod
    def walk(cls, _data: Mapping, path: PathType, *, sep: str=".") -> WalkResultType:
        """Walk a path to determine the container (Mapping, Sequence) which holds
        the last key.

        TODO: Support
        'path' is very flexible, e.g. "a.b.c", "a[1].b", "a.1.b", "a/b/c",
        "[a][b][c]", ["a", "b", "c"], ("a", "b", "c",), ["a", "b.c"]

        :param _data: the Mapping like structure
        :param path: the path to identify the element
        :param sep: 'path' separator. Default: '.'
        :return: The final container and key/index to access the element
        """

        if isinstance(path, str):
            keys = path.split(sep)
        elif isinstance(path, int):
            keys = path
        else:
            keys = path

        assert keys
        last = keys[-1]
        key = ""
        for key in keys[0:-1]:
            _data = _data[key]

        return (_data, last)

    @classmethod
    def get(cls, _data: Mapping, path: PathType, *, sep: str=".", default: Any = DEFAULT) -> Any:
        """Similar to dict.get(), but with deep path support
        """
        try:
            _data, key = cls.walk(_data, path, sep=sep)
            return _data.get(key, default)
        except Exception as exc:
            raise ConfigException(f"ConfigDict: Value not found: '{path}'") from exc

    @classmethod
    def delete(cls, _data: Mapping, path: PathType, *, sep: str=".", exception: bool = True) -> Any:
        """Similar to 'del dict[key]', but with deep path support
        """
        try:
            _data, key = cls.walk(_data, path, sep=sep)
            del _data[key]
        except Exception as exc:    # pylint: disable=broad-exception-caught
            if exception:
                raise ConfigException(f"ConfigDict: Value not found: '{path}'") from exc

    @classmethod
    def set(cls, _data: Mapping, path: PathType, value: Any, *, sep: str=".") -> Any:
        """Similar to 'dict[key] = valie', but with deep path support
        """
        try:
            _data, key = cls.walk(_data, path, sep=sep)
            _data[key] = value
        except Exception as exc:
            raise ConfigException(f"ConfigDict: Value not found: '{path}'") from exc

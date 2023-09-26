#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Assuming a deep Mapping- and Sequence-like structure, walk along
a path and support dict-like get(), set() and delete() operations
and the elements.
"""

import re
import logging
from typing import Any, Iterable, Mapping, Tuple, Type, Sequence, Optional, Union
from .convert import convert

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
    def walk(cls, _data: Mapping, path: PathType, *, on_missing: Optional[callable] = None, sep: str=".") -> WalkResultType:
        """Walk a path to determine the container (Mapping, Sequence) which holds
        the last key.

        'path' is very flexible, e.g. "a.b.c", "a[1].b", "a.1.b", "a/b/c",
        "[a][b][c]", ["a", "b", "c"], ("a", "b", "c",), ["a", "b.c"]

        :param _data: the Mapping like structure
        :param path: the path to identify the element
        :param sep: 'path' separator. Default: '.'
        :return: The final container and key/index to access the element
        """

        keys = cls.normalize_path(path, sep=sep)

        assert keys
        last = keys[-1]
        key = ""
        for i, key in enumerate(keys[0:-1]):
            try:
                _data = _data[key]
            except:     # pylint: disable=bare-except
                if callable(on_missing):
                    _data[key] = new_data = on_missing(_data, key, keys[0 : i])
                    _data = new_data
                else:
                    raise

        return (_data, last)

    @classmethod
    def get(cls, _data: Mapping, path: PathType, default: Any = DEFAULT, *, sep: str=".") -> Any:
        """Similar to dict.get(), but with deep path support
        """
        try:
            _data, key = cls.walk(_data, path, sep=sep)
            return _data[key]
        except Exception as exc:
            if default is not DEFAULT:
                return default

            raise ConfigException(f"ConfigDict: Value not found: '{path}'") from exc

    @classmethod
    def _get_old(cls, _data: Mapping, key: str|int) -> Any:
        try:
            return _data[key]
        except KeyError:
            return None

    @classmethod
    def delete(cls, _data: Mapping, path: PathType, *, sep: str=".", exception: bool = True) -> Any:
        """Similar to 'del dict[key]', but with deep path support
        """
        try:
            _data, key = cls.walk(_data, path, sep=sep)
            old_value = cls._get_old(_data, key)

            del _data[key]
            return old_value

        except Exception as exc:    # pylint: disable=broad-exception-caught
            if exception:
                raise ConfigException(f"ConfigDict: Value not found: '{path}'") from exc

        return None

    @classmethod
    def set(cls, _data: Mapping, path: PathType, value: Any, *, create_missing: Union[callable, bool, dict]=False, sep: str=".") -> Any:
        """Similar to 'dict[key] = valie', but with deep path support.

        Limitations:
          - is not possible to append elements to a Sequence. You need to get() the list
            and manually append the element.
        """

        def on_missing_handler(_data: Mapping|Sequence, key: str|int, path: tuple) -> Mapping|Sequence:
            if isinstance(key, int):
                if isinstance(_data, Sequence):
                    raise ConfigException(f"Can not create missing [] nodes: '{path}'")
                else:
                    raise ConfigException(f"Expected a list but found: '{path}' = {type(_data)}")

            return {}

        def on_missing_handler_dict(_, key: str|int, __) -> Mapping|Sequence:
            value = create_missing.get(key, dict)
            if isinstance(value, type):
                return value()

            return value

        if isinstance(create_missing, bool):
            on_missing = on_missing_handler if create_missing else None
        elif callable(create_missing):
            on_missing = create_missing
        elif isinstance(create_missing, dict):
            on_missing = on_missing_handler_dict

        try:
            _data, key = cls.walk(_data, path, sep=sep, on_missing=on_missing)
            old_value = cls._get_old(_data, key)

            _data[key] = value
            return old_value

        except Exception as exc:
            raise ConfigException(f"ConfigDict: Value not found: '{path}'") from exc

    @classmethod
    def normalize_path(cls, path: PathType, *, sep: str=".") -> Tuple[str|int, ...]:
        """Convert flexible path into normalized Tuple

        'path' is very flexible, e.g. "a.b.c", "a[1].b", "a.1.b", "a/b/c",
        "[a][b][c]", ["a", "b", "c"], ("a", "b", "c",), ["a", "b.c"]

        :param path: the path to identify the element
        :param sep: 'path' separator. Default: '.'
        :return: normalized path, with each path segment a tuple element

        """
        rtn = cls._normalize_path_raw(path, sep)
        last_len = len(path) if isinstance(path, (list, Tuple)) else 1
        while last_len != len(rtn):
            last_len = len(rtn)
            rtn = cls._normalize_path_raw(rtn, sep)

        return rtn

    @classmethod
    def _normalize_path_raw(cls, path: PathType, sep: str) -> list[str|int]:
        """Internal: one iteration of normalizing a path. Might be that it
        must be called multiple times.
        """
        if isinstance(path, str):
            path = re.sub(r"\[(.*?)\]", f"{sep}\\1", path)

            # Remove all leading separators
            while path.startswith(sep):
                path = path[1:]

            keys = path.split(sep)
        elif isinstance(path, int):
            keys = [path]
        elif isinstance(path, Sequence):
            keys = []
            for elem in path:
                keys.extend(cls._normalize_path_raw(elem, sep))
        else:
            raise ConfigException(f"Invalid config path: Unknown type: '{path}'")

        keys = [convert(x) for x in keys]
        return keys

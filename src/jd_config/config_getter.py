#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import logging
from typing import Any, Iterable, Mapping, Tuple, Type
from .jd_config import ConfigException

logger = logging.getLogger(__name__)


DEFAULT = object()

PathType: Type = str | int | Iterable

class ConfigGetter:

    @classmethod
    def walk(cls, _data: Mapping, path: PathType, sep: str=".") -> Tuple[Any, Any]:

        # TODO: Support
        # "a.b.c", "a[1].b", "a/b/c", "[a][b][c]", ["a", "b", "c"], ("a", "b", "c",), ["a", "b.c"]
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
        try:
            _data, key = cls.walk(_data, path, sep)
            return _data.get(key, default)
        except Exception as exc:
            raise ConfigException(f"ConfigDict: Value not found: '{path}'") from exc

    @classmethod
    def delete(cls, _data: Mapping, path: PathType, *, sep: str=".", exception: bool = True) -> Any:
        try:
            _data, key = cls.walk(_data, path, sep)
            del _data[key]
        except Exception as exc:    # pylint: disable=broad-exception-caught
            if exception:
                raise ConfigException(f"ConfigDict: Value not found: '{path}'") from exc

    @classmethod
    def set(cls, _data: Mapping, path: PathType, value: Any, *, sep: str=".") -> Any:
        try:
            _data, key = cls.walk(_data, path, sep)
            _data[key] = value
        except Exception as exc:
            raise ConfigException(f"ConfigDict: Value not found: '{path}'") from exc

#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Extended standard dict like getter to also support deep paths, and also
search patterns, such as 'a..c', 'a.*.c'
"""

import logging
from typing import Any, Mapping

from .utils import NonStrSequence, PathType, ConfigException
from .config_path import ConfigPath
from .objwalk import ObjectWalker

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


DEFAULT = object()


class DeepGetterWithSearch:
    """Extended standard dict like getter to also support deep paths, and also
    search patterns, such as 'a..c', 'a.*.c'
    """

    def __init__(
        self, data: Mapping | NonStrSequence, path: PathType, *, _memo=()
    ) -> None:
        self._data = data
        self._path = path
        self._memo = _memo

    def cb_get(self, data, key) -> Any:
        """Retrieve the element. Subclasses may expand it, e.g. to resolve
        placeholders
        """
        return data[key]

    def _cb_get_internal(self, data, key) -> Any:
        """Internal:"""
        try:
            return self.cb_get(data, key)
        except (KeyError, IndexError) as exc:
            return self.on_missing(data, key, exc)

    def on_missing(self, data, key, exc) -> Any:
        """A callback invoked, if a path can not be found.

        Subclasses may auto-create elements if needed.
        By default, the exception is re-raised.
        """
        return self.on_missing_default(data, key, exc)

    def on_missing_default(self, data, key, exc) -> Any:
        """A callback invoked, if a path can not be found.

        Subclasses may auto-create elements if needed.
        By default, the exception is re-raised.
        """
        raise ConfigException(f"Config not found: '{key}'") from exc

    def get(self, path: PathType, default: Any = DEFAULT) -> Any:
        """Extended standard dict like getter to also support deep paths, and also
        search patterns, such as 'a..c', 'a.*.c'
        """

        try:
            data, _ = self.find(path)
            return data
        except (KeyError, IndexError, ConfigException) as exc:
            if default != DEFAULT:
                return default

            if isinstance(exc, ConfigException):
                raise

            raise ConfigException(f"Unable to get config from path: '{path}'") from exc

    def get_path(self, path: PathType) -> list[str | int]:
        """Determine the real path by replacing the search patterns"""

        _, path = self.find(path)
        return path

    def find(self, path: PathType) -> (Any, list[str | int]):
        """Determine the value and the real path by replacing the search patterns"""

        target = ConfigPath.normalize_path(path)

        path: tuple[str | int] = ()
        data = self._data

        i = 0
        while i < len(target):
            elem = target[i]
            if elem == ConfigPath.PAT_ANY_KEY:
                i += 1
                data, path = self.on_any_key(data, target[i], path)
            elif elem == ConfigPath.PAT_ANY_IDX:
                i += 1
                data, path = self.on_any_idx(data, target[i], path)
            elif elem == ConfigPath.PAT_DEEP:
                i += 1
                data, path = self.on_any_deep(data, target[i], path)
            else:
                data = self._cb_get_internal(data, elem)

            path = path + (target[i],)
            i += 1

        return data, path

    def on_any_key(
        self, data: Mapping, elem: str, path: tuple[str | int]
    ) -> (Any, Any):
        """Callback if 'a.*.c' was found"""

        if not isinstance(data, Mapping):
            raise ConfigException(f"Expected a Mapping: '{path}'")

        for key in data.keys():
            # Allow to resolve placeholder if necessary
            value = self._cb_get_internal(data, key)

            if isinstance(value, Mapping) and isinstance(elem, str):
                if elem in value:
                    path = path + (key,)
                    return value[elem], path
            elif isinstance(value, NonStrSequence) and isinstance(elem, int):
                if 0 <= elem < len(value):
                    path = path + (key,)
                    return value[elem], path

        path = path + ("*", elem)
        raise ConfigException(f"Key not found: '{path}'")

    def on_any_idx(
        self, data: NonStrSequence, elem: int, path: tuple[str | int]
    ) -> (Any, Any):
        """Callback if 'a[*].b' was found"""

        if not isinstance(data, NonStrSequence):
            raise ConfigException(f"Expected a Sequence, but not a string: '{path}'")

        for key, value in enumerate(data):
            # Allow to resolve placeholder if necessary
            value = self._cb_get_internal(data, key)

            if isinstance(value, Mapping) and isinstance(elem, str):
                if elem in value:
                    path = path + (key,)
                    return value[elem], path
            elif isinstance(value, NonStrSequence) and isinstance(elem, int):
                if 0 <= elem < len(value):
                    path = path + (key,)
                    return value[elem], path

        path = path + ("[*]", elem)
        raise ConfigException(f"Key not found: '{path}'")

    def on_any_deep(
        self, data: Mapping | NonStrSequence, elem: str | int, path: list[str | int]
    ) -> (Any, Any):
        """Callback if 'a..b' was found"""

        for event in ObjectWalker.objwalk(data, nodes_only=False, cb_get=self.cb_get):
            if event.path and event.path[-1] == elem:
                for node in event.path:
                    # Allow to resolve placeholder if necessary
                    data = self._cb_get_internal(data, node)
                    path = path + (node,)

                path = path[:-1]
                return data, path

        path = path + ("", elem)
        raise ConfigException(f"Key not found: '{path}'")

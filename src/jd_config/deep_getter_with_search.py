#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Extended standard dict like getter to also support deep paths, and also
search patterns, such as 'a..c', 'a.*.c'
"""

import logging
from typing import Any, Mapping, Sequence

from .config_path import ConfigPath, PathType
from .objwalk import ObjectWalker, NonStrSequence

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


DEFAULT = object()


class DeepGetterWithSearch:
    """Extended standard dict like getter to also support deep paths, and also
    search patterns, such as 'a..c', 'a.*.c'
    """

    def get(
        self, data: Mapping | Sequence, path: PathType, default: Any = DEFAULT
    ) -> Any:
        """Extended standard dict like getter to also support deep paths, and also
        search patterns, such as 'a..c', 'a.*.c'
        """
        try:
            data, _ = self.find(data, path)
            return data
        except (KeyError, IndexError):
            if default == DEFAULT:
                raise

            return default

    def get_path(self, data: Mapping | Sequence, path: PathType) -> list[str | int]:
        """Determine the real path by replacing the search patterns"""

        _, path = self.find(data, path)
        return path

    def find(
        self, data: Mapping | Sequence, path: PathType
    ) -> (Any, list[str | int]):
        """Determine the value and the real path by replacing the search patterns"""

        path = ConfigPath.normalize_path(path)

        current_path = []

        i = 0
        while i < len(path):
            elem = path[i]
            if elem == ConfigPath.PAT_ANY_KEY:
                i += 1
                data = self.on_any_key(data, path[i], current_path)
            elif elem == ConfigPath.PAT_ANY_IDX:
                i += 1
                data = self.on_any_idx(data, path[i], current_path)
            elif elem == ConfigPath.PAT_DEEP:
                i += 1
                data = self.on_any_deep(data, path[i], current_path)
            else:
                data = data[elem]

            current_path.append(path[i])
            i += 1

        return data, current_path

    def on_any_key(
        self, data: Mapping | Sequence, elem: str | int, current_path: list[str | int]
    ) -> Mapping | Sequence:
        """Callback if 'a.*.c' was found"""

        if not isinstance(data, Mapping):
            raise KeyError(f"Expected a Mapping: '{current_path}'")

        for key, value in data.items():
            if isinstance(value, Mapping) and isinstance(elem, str):
                if elem in value:
                    current_path.append(key)
                    return value[elem]
            elif isinstance(value, NonStrSequence) and isinstance(elem, int):
                if 0 <= elem < len(value):
                    current_path.append(key)
                    return value[elem]

        path = current_path + ["*", elem]
        raise KeyError(f"Key not found: '{path}'")

    def on_any_idx(
        self, data: Mapping | Sequence, elem: str | int, current_path: list[str | int]
    ) -> Mapping | Sequence:
        """Callback if 'a[*].b' was found"""

        if not isinstance(data, NonStrSequence):
            raise KeyError(f"Expected a Sequence: '{current_path}'")

        for i, value in enumerate(data):
            if isinstance(value, Mapping) and isinstance(elem, str):
                if elem in value:
                    current_path.append(i)
                    return value[elem]
            elif isinstance(value, NonStrSequence) and isinstance(elem, int):
                if 0 <= elem < len(value):
                    current_path.append(i)
                    return value[elem]

        current_path[-1] += f"[*]"
        path = current_path + [elem]
        raise KeyError(f"Key not found: '{path}'")

    def on_any_deep(
        self, data: Mapping | Sequence, elem: str | int, current_path: list[str | int]
    ) -> Mapping | Sequence:
        """Callback if 'a..b' was found"""

        for event in ObjectWalker.objwalk(data, nodes_only=False):
            if event.path and event.path[-1] == elem:
                for node in event.path:
                    data = data[node]
                    current_path.append(node)

                current_path.pop()
                return data

        path = current_path + ["", elem]
        raise KeyError(f"Key not found: '{path}'")

#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Normalize config paths such as "a.b.c", "a.b[2].c", "a..c", "a.*.c", "a.b[*].c",
["a.b.c"], ["a", "b.c"], ["a", ["b.c"]], "a/b/c"
"""

import logging
import re
from typing import Any, Iterable, Iterator, Optional, Sequence, Union

from .utils import ConfigException

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)

PathType = Union[str, int, Iterable[str | int], "CfgPath"]


class CfgPath(Sequence):
    """Dict-like get, set, delete and find operations on deep
    Mapping- and Sequence-like structures.
    """

    # Allows to change the global default
    # Test in the sequence provided
    # Because of "../a", "." should always be last
    DEFAULT_SEP: str = "/."

    PARENT_DIR: str = ".."
    CURRENT_DIR: str = "."

    def __init__(self, path: PathType = (), sep: str = DEFAULT_SEP) -> None:
        self.path = self.normalize(path, sep=sep)

    @classmethod
    def flatten(cls, path: PathType) -> Iterator[str | int]:
        """Flatten a list of list"""

        if isinstance(path, (list, tuple, range)):
            for elem in path:
                yield from cls.flatten(elem)
        else:
            yield path

    @classmethod
    def split_path(cls, path: str, sep: str) -> list[str]:
        """Split the path by the first separator char found

        E.g. 'split_path("a.b.c", "/.")' => ["a", "b", "c"]
        """

        if not isinstance(path, str) or len(sep) == 0:
            return [path]

        if len(sep) == 1:
            return path.split(sep)

        if path in [cls.PARENT_DIR, cls.CURRENT_DIR]:
            return [path]

        for elem in sep:
            if elem in path:
                return path.split(elem)

        return [path]

    @classmethod
    def flatten_and_split_path(cls, path: PathType, sep: str) -> Iterable[str | int]:
        """Flatten a list of list, and further split the str elements by a separator"""

        for elem in cls.flatten(path):
            data = cls.split_path(elem, sep)

            for elem_2 in data:
                yield elem_2

    @classmethod
    def _append_to_path_str(cls, path: str, elem: str | int, sep: str) -> str:
        """Convert a element of a normalized path into a string"""

        if isinstance(elem, int):
            path += f"[{str(elem)}]"
        else:
            if path or elem == "":
                path += sep

            path += elem

        return path

    def to_str(self, sep: Optional[str] = None) -> str:
        """Convert a normalized path into a string"""

        if sep is None:
            for i in reversed(self.DEFAULT_SEP):
                found = any(isinstance(elem, str) and i in elem for elem in self.path)
                if not found:
                    sep = i
                    break
            else:
                sep = "."

        rtn = ""
        for elem in self.path:
            rtn = self._append_to_path_str(rtn, elem, sep)

        return rtn

    @classmethod
    def normalize(
        cls, path: PathType, *, sep: str = DEFAULT_SEP
    ) -> tuple[str | int, ...]:
        """Convert flexible path into normalized list

        'path' is simple: e.g. "a.b.c", "a[1].b", ("a[1]", "b", "c"),
        ["a", "b.c"], ["a.b.c"], ["a", ["b", ["c"]]]

        But also:
        - "a.*.c": match any key
        - "a[*].b": match any index
        - "a..c": recursively match everything

        :param path: the path to identify the element
        :param sep: 'path' separator. Default: '.'
        :return: normalized path
        """
        if sep is None:
            sep = cls.DEFAULT_SEP

        if not path:
            return ()

        if isinstance(path, CfgPath):
            return path.path

        rtn = []
        pat = re.compile(r"\s*([^\[\]]*)\s*((?:\[\s*(\d+|\*)\s*\]\s*)*)")
        for elem in cls.flatten_and_split_path(path, sep):
            if elem != 0 and not elem:
                raise ConfigException(f"Invalid config path: empty element: '{path}'")

            if isinstance(elem, int):
                rtn.append(elem)
                continue

            if isinstance(elem, str):
                if (elem != cls.PARENT_DIR) and (cls.PARENT_DIR in elem):
                    raise ConfigException(
                        f"Invalid config path: misplaced '..': '{path}'"
                    )

                match = pat.fullmatch(elem)
                if match:
                    cls._normalize_path_elem(match.group(1), match.group(2), rtn, path)
                    continue

            raise ConfigException(
                f"Invalid config path: Unknown type: '{elem}' in '{path}'"
            )

        cleaned = cls._cleanup_path(rtn)
        return tuple(cleaned)

    @classmethod
    def _normalize_path_elem(cls, key, index, rtn: list, path):
        if key:
            rtn.append(key)
        elif rtn:
            raise ConfigException(
                f"Invalid config path: Expected 'name[key]', but found: '{path}'"
            )

        if index:
            index = index[1:-1]
            index = re.split(r"\s*\]\s*\[\s*", index)
            for cleaned in index:
                try:
                    cleaned = cls._on_index(cleaned)
                    if cleaned is not None:
                        rtn.append(cleaned)

                except ValueError as exc:
                    raise ConfigException(
                        f"Invalid config index: Expected 'name[key]', but found: '{path}'"
                    ) from exc

        return rtn

    @classmethod
    def _on_index(cls, text) -> Any:
        return int(text) if text is not None else None

    @classmethod
    def _cleanup_path(cls, rtn: list):
        cleaned = []
        for elem in rtn:
            if not cleaned:
                cleaned.append(elem)
            elif elem == cls.PARENT_DIR:
                cleaned.pop()
            elif elem == cls.CURRENT_DIR:
                pass  # Nothing to do
            else:
                cleaned.append(elem)

        if len(cleaned) == 1 and cleaned[0] == cls.CURRENT_DIR:
            cleaned.pop()

        return cleaned

    def match(self, other: object) -> bool:
        """Compare two paths, taking search pattern into account

        E.g. "a.b.c" == "a..c" == "a.*.c"
        """

        if isinstance(other, (str, int, Sequence)):
            other = CfgPath(other)

        if not isinstance(other, CfgPath):
            return False

        return self.path == other.path

    def __getitem__(self, key):
        return self.path[key]

    def __len__(self) -> int:
        return len(self.path)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, (str, int, Sequence)):
            other = CfgPath(other)

        if isinstance(other, CfgPath):
            return self.path == other.path

        return False

    def append(self, value: PathType) -> "CfgPath":
        """Append 'value'"""
        value = CfgPath(value)
        self.path = self.path + value.path
        return self

    def pop(self) -> "CfgPath":
        """Pop the last elem from the path"""
        self.path = self.path[:-1]
        return self

    def __add__(self, value: PathType) -> "CfgPath":
        value = CfgPath(value)
        path = self.path + value.path
        return CfgPath(path)

    def __hash__(self):
        return hash(self.path)

    def __str__(self) -> str:
        return self.to_str()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}('{self.to_str()}')"

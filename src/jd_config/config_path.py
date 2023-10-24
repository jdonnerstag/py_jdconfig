#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Normalize config paths such as "a.b.c", "a.b[2].c", "a..c", "a.*.c", "a.b[*].c",
["a.b.c"], ["a", "b.c"], ["a", ["b.c"]], "a/b/c"
"""

import logging
import re
from typing import Iterable, Iterator, Sequence, Union

from .utils import ConfigException

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)

PathType = Union[str, int, Iterable[str | int], "CfgPath"]


class CfgPath(Sequence):
    """Dict-like get, set, delete and find operations on deep
    Mapping- and Sequence-like structures.
    """

    # Allows to change the global default
    DEFAULT_SEP = "."

    PAT_ANY_KEY = "*"
    PAT_ANY_IDX = "%"
    PAT_DEEP = ""

    SEARCH_PATTERN = (PAT_ANY_KEY, PAT_ANY_IDX, PAT_DEEP)

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
    def flatten_and_split_path(cls, path: PathType, sep: str) -> Iterable[str | int]:
        """Flatten a list of list, and further split the str elements by a separator"""

        for elem in cls.flatten(path):
            if isinstance(elem, str):
                for elem_2 in elem.split(sep):
                    yield elem_2
            else:
                yield elem

    @classmethod
    def _append_to_path_str(cls, path: str, elem: str | int, sep: str) -> str:
        """Convert a element of a normalized path into a string"""

        if isinstance(elem, int):
            path += f"[{str(elem)}]"
        elif elem == cls.PAT_ANY_IDX:
            path += "[*]"
        else:
            if path or elem == "":
                path += sep

            path += elem

        return path

    def to_str(self, sep: str = DEFAULT_SEP) -> str:
        """Convert a normalized path into a string"""

        rtn = ""
        for elem in self.path:
            rtn = self._append_to_path_str(rtn, elem, sep)

        return rtn

    @classmethod
    def is_search_pattern(cls, elem: str | int) -> bool:
        """Check whether path has pattern like "c..c32", "c.c2[*].c32", "c.*.c32" """

        if not isinstance(elem, str):
            return False

        return elem in cls.SEARCH_PATTERN

    def has_search_pattern(self) -> bool:
        """Check whether path has pattern like "c..c32", "c.c2[*].c32", "c.*.c32" """

        return any(self.is_search_pattern(x) for x in self.path)

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
            if isinstance(elem, int):
                rtn.append(elem)
                continue
            if isinstance(elem, str):
                match = pat.fullmatch(elem)
                if match:
                    cls._normalize_path_elem(match.group(1), match.group(2), rtn)
                    continue

            raise ConfigException(
                f"Invalid config path: Unknown type: '{elem}' in '{path}'"
            )

        cleaned = cls._cleanup_path(rtn)
        if cleaned and cleaned[-1] in [cls.PAT_DEEP, cls.PAT_ANY_KEY]:
            raise ConfigException(
                f"Config path must not end with with a selector: '{path}'"
            )

        return tuple(cleaned)

    @classmethod
    def _normalize_path_elem(cls, key, index, rtn: list):
        if key == cls.PAT_ANY_KEY:
            rtn.append(cls.PAT_ANY_KEY)
        elif not key:
            if not index:
                rtn.append(cls.PAT_DEEP)
        elif key:
            rtn.append(key)

        if index:
            index = index[1:-1]
            index = re.split(r"\s*\]\s*\[\s*", index)
            for cleaned in index:
                if cleaned == "*":
                    rtn.append(cls.PAT_ANY_IDX)
                elif cleaned is not None:
                    rtn.append(int(cleaned))

        return rtn

    @classmethod
    def _cleanup_path(cls, rtn: list):
        cleaned = []
        last = None
        for elem in rtn:
            if last is None:
                last = elem
                cleaned.append(elem)
            elif elem not in [cls.PAT_DEEP, cls.PAT_ANY_KEY, cls.PAT_ANY_IDX]:
                last = elem
                cleaned.append(elem)
            elif last not in [cls.PAT_DEEP, cls.PAT_ANY_KEY, cls.PAT_ANY_IDX]:
                last = elem
                cleaned.append(elem)
            elif last == cls.PAT_DEEP:
                pass
            elif elem in [cls.PAT_ANY_KEY, cls.PAT_ANY_IDX]:
                last = elem
                cleaned.append(elem)
            else:  # last == ANY_INDEX and elem in [RECURSIVE_KEY, ANY_INDEX]
                last = elem
                cleaned.pop()
                cleaned.append(elem)

        return cleaned

    def match(self, other: object) -> bool:
        """Compare two paths, taking search pattern into account

        E.g. "a.b.c" == "a..c" == "a.*.c"
        """

        if isinstance(other, (str, int, Sequence)):
            other = CfgPath(other)

        if not isinstance(other, CfgPath):
            return False

        path_1 = self.path
        path_2 = other.path

        i_1 = 0
        i_2 = 0
        while i_1 < len(path_1):
            elem_1 = path_1[i_1]
            elem_2 = path_2[i_2]
            i_1 += 1

            if elem_2 in [self.PAT_ANY_KEY, self.PAT_ANY_IDX]:
                i_2 += 1
                if i_1 < len(path_1) and isinstance(path_1[i_1], int):
                    i_1 += 1
            elif elem_2 == self.PAT_DEEP:
                if elem_1 != path_2[i_2 + 1]:
                    continue

                i_2 += 2
            else:
                if elem_1 != elem_2:
                    return False

                i_2 += 1

            if i_2 >= len(path_2):
                return True

        return False

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
        value = CfgPath(value)
        self.path = self.path + value.path
        return self

    def pop(self) -> "CfgPath":
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

#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Normalize config paths such as "a.b.c", "a.b[2].c", "a..c", "a.*.c", "a.b[*].c",
["a.b.c"], ["a", "b.c"], ["a", ["b.c"]], "a/b/c"
"""

import logging
from typing import Any, Sequence

from .config_path import CfgPath, PathType
from .utils import ConfigException

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


class ExtendedCfgPath(CfgPath):
    """Extend the default CfgPath with support for search patterns, such
    as "a.*.c", "a.b[*].c", or "a.**.c"
    """

    PAT_ANY_KEY: str = "*"
    PAT_ANY_IDX: str = "%"
    PAT_DEEP: str = "**"

    SEARCH_PATTERN = (PAT_ANY_KEY, PAT_ANY_IDX, PAT_DEEP)

    @classmethod
    def _append_to_path_str(cls, path: str, elem: str | int, sep: str) -> str:
        """Convert a element of a normalized path into a string"""

        if elem == cls.PAT_ANY_IDX:
            return path + "[*]"

        return super()._append_to_path_str(path, elem, sep)

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
        cls, path: PathType, *, sep: str = CfgPath.DEFAULT_SEP
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
        rtn = super().normalize(path, sep=sep)
        if cls._ends_with_invalid_search_key(rtn):
            raise ConfigException(
                f"Config path must not end with with a selector: '{path}'"
            )

        return rtn

    @classmethod
    def _ends_with_invalid_search_key(cls, cleaned):
        if not cleaned:
            return cleaned

        last = len(cleaned) - 1
        while last >= 0:
            if cleaned[last] != cls.PARENT_DIR:
                break

            last -= 1

        return cleaned[last] in [cls.PAT_DEEP, cls.PAT_ANY_KEY]

    @classmethod
    def _on_index(cls, text) -> Any:
        if text == "*":
            return cls.PAT_ANY_IDX

        return super()._on_index(text)

    @classmethod
    def _cleanup_path(cls, rtn: list):
        if len(rtn) >= 2:
            if rtn[-1] == cls.PARENT_DIR and rtn[-2] == cls.PAT_DEEP:
                rtn.pop()

        rtn = super()._cleanup_path(rtn)

        cleaned = []
        last = None
        for elem in rtn:
            if not cleaned:
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

        E.g. "a.b.c" == "a.**.c" == "a.*.c"
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

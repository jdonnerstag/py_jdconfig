#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Assuming a deep Mapping- and Sequence-like structure, walk along
a path and support dict-like get(), set() and delete() operations
and the elements.
"""

import re
import logging
from typing import (
    Any,
    Iterable,
    Iterator,
    Mapping,
    Tuple,
    Type,
    Sequence,
    Optional,
    Union,
)

from .string_converter_mixin import StringConverterMixin
from .objwalk import ObjectWalker

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


DEFAULT = object()

PathType: Type = str | int | Iterable[str | int]

WalkResultType: Type = Union[Tuple[Mapping, str], Tuple[Sequence, int]]


PAT_ANY = "*"
PAT_DEEP = ""


def flatten(path: PathType) -> Iterator[str | int]:
    """Flatten a list of list"""

    if isinstance(path, (list, tuple, range)):
        for elem in path:
            yield from flatten(elem)
    else:
        yield path


class ConfigException(Exception):
    """Base class for Config Exceptions"""


class ConfigGetter(StringConverterMixin):
    """Dict-like get, set and delete operations on deep Mapping-
    and Sequence-like structures.
    """

    @classmethod
    def _flatten_and_split_path(cls, path: PathType, sep: str) -> Iterable[str | int]:
        """Flatten a list of list, and further split the str elements by a separator"""

        for elem in flatten(path):
            if isinstance(elem, str):
                for elem_2 in elem.split(sep):
                    yield elem_2
            else:
                yield elem

    @classmethod
    def _walk_path(
        cls, data: Mapping | Sequence, path: list[str | int]
    ) -> WalkResultType:
        """Walk a path to determine the container (Mapping, Sequence) which holds
        the last key.

        :param data: the Mapping like structure
        :param path: a already normalized path
        """

        if not path:
            return (data, path)

        last = path[-1]
        for elem in path[:-1]:
            data = data[elem]

        return (data, last)

    @classmethod
    def _walk(
        cls,
        data: Mapping | Sequence,
        path: list[str | int],
        on_missing: Optional[callable] = None,
        replace_path: bool = False,
    ) -> WalkResultType:
        """Walk a path to determine the container (Mapping, Sequence) which holds
        the last key. This is mostly an internal function.

        'path' is simple: e.g. "a.b.c", "a[1].b", ("a[1]", "b", "c"),
        ["a", "b.c"], ["a.b.c"]

        :param data: the Mapping like structure
        :param path: a already normalized path
        :param on_missing: an optional callable which gets invoked upon missing keys
        :return: The final container and key/index to access the element
        """

        if not path:
            return (data, path)

        last = path[-1]
        for i, key in enumerate(path[0:-1]):
            if (isinstance(data, Mapping) and key not in data) or (
                isinstance(data, Sequence) and (key < 0 or key >= len(data))
            ):
                if callable(on_missing):
                    data[key] = new_data = on_missing(data, key, path[0:i])
                    data = new_data
                else:
                    raise ConfigException(f"Config path not found: {path}")
            else:
                prev_data = data
                data = data[key]
                if isinstance(data, str) or not isinstance(data, (Mapping, Sequence)):
                    if replace_path is True:
                        if callable(on_missing):
                            prev_data[key] = new_data = on_missing(
                                prev_data, key, path[0:i]
                            )
                            data = new_data
                            continue

                    raise ConfigException(
                        f"Expected a list or dict, but found a value at {path}"
                    )

        if isinstance(data, (Mapping, Sequence)):
            return (data, last)

        raise ConfigException(
            f"Expect to find a list or dict, but found a value at {path}"
        )

    @classmethod
    def _walk_and_find(
        cls,
        data: Mapping | Sequence,
        path: list[str | int],
    ) -> WalkResultType:
        """Combine walk() and find() to support extended paths

        Examples: "a.b.c", "a[1].b", ("a[1]", "b", "c"),
        ["a", "b.c"], ["a.b.c"]

        And also: "c..c32", "c.c2[*].c32", "c.*.c32"

        :param data: the Mapping like structure
        :param path: a already normalized path
        """

        # Maybe path has pattern and like "c..c32", "c.c2[*].c32", "c.*.c32"
        if any((x == PAT_DEEP) or (PAT_ANY in x) for x in path if isinstance(x, str)):
            deep_path = cls.get_path(data, path)
            if deep_path:
                last = deep_path[-1]
                rtn = data
                for elem in deep_path[:-1]:
                    rtn = rtn[elem]

                return (rtn, last)

        # First try and walk the path
        try:
            data, key = cls._walk(data, path, on_missing=None)
            return (data, key)
        except Exception as exc:  # pylint: disable=bare-except
            raise ConfigException(f"ConfigDict: Value not found: '{path}'") from exc

    @classmethod
    def get(
        cls, data: Mapping, path: PathType, default: Any = DEFAULT, *, sep: str = "."
    ) -> Any:
        """Similar to dict.get(), but with deep path support.

        Example paths: "a.b.c", "a[1].b", ("a[1]", "b", "c"),
        ["a", "b.c"], ["a.b.c"]

        And also: "c..c32", "c.c2[*].c32", "c.*.c32"

        :param data: the Mapping like structure
        :param path: the path to identify the element
        :param sep: 'path' separator. Default: '.'
        :return: The config value
        """

        path = cls.normalize_path(path, sep=sep)

        try:
            data, key = cls._walk_and_find(data, path)
            return data[key]
        except Exception as exc:  # pylint: disable=W0718
            if default != DEFAULT:
                return default

            if isinstance(exc, ConfigException):
                raise

            raise ConfigException(f"ConfigDict: Value not found: '{path}'") from exc

    @classmethod
    def _get_old(cls, data: Mapping, key: str | int) -> Any:
        try:
            return data[key]
        except KeyError:
            return None

    @classmethod
    def delete(
        cls,
        data: Mapping | Sequence,
        path: PathType,
        *,
        sep: str = ".",
        exception: bool = True,
    ) -> Any:
        """Similar to 'del dict[key]', but with deep path support"""

        path = cls.normalize_path(path, sep=sep)

        try:
            data, key = cls._walk_and_find(data, path)
            old_value = cls._get_old(data, key)

            del data[key]
            return old_value

        except Exception as exc:  # pylint: disable=broad-exception-caught
            if exception:
                raise ConfigException(f"ConfigDict: Value not found: '{path}'") from exc

        return None

    @classmethod
    def _create_missing(
        cls,
        data: Mapping | Sequence,
        path: list[str | int],
        create_missing: Union[callable, bool, dict],
        replace_path: bool = False,
    ) -> WalkResultType:
        """Create any missing elem on the path

        Limitations:
          - is not possible to append elements to a Sequence. You need to get() the list
            and manually append the element.
        """

        def on_missing_handler(
            _data: Mapping | Sequence, key: str | int, path: tuple
        ) -> Mapping | Sequence:
            if isinstance(key, int):
                if isinstance(_data, Sequence):
                    raise ConfigException(f"Can not create missing [] nodes: '{path}'")

                raise ConfigException(
                    f"Expected a list but found: '{path}' = {type(_data)}"
                )

            return {}

        def on_missing_handler_dict(_, key: str | int, __) -> Mapping | Sequence:
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

        data, key = cls._walk(data, path, on_missing, replace_path)
        return (data, key)

    @classmethod
    def set(
        cls,
        data: Mapping | Sequence,
        path: PathType,
        value: Any,
        *,
        create_missing: Union[callable, bool, dict] = False,
        replace_value: bool = True,
        replace_path: bool = False,
        sep: str = ".",
    ) -> Any:
        """Similar to 'dict[key] = valie', but with deep path support.

        Limitations:
          - is not possible to append elements to a Sequence. You need to get() the list
            and manually append the element.

        :param data: the Mapping like structure
        :param path: the path to identify the element
        :param value: the new value
        :param create_missing: what to do if a path element is missing
        :param replace_value: If false, then do not replace an existing value
        :param replace_path: If true, then consider parts missing, of their not containers
        :param sep: 'path' separator. Default: '.'
        """

        path = cls.normalize_path(path, sep=sep)
        data, key = cls._create_missing(data, path, create_missing, replace_path)
        old_value = cls._get_old(data, key)

        try:
            data[key] = value
            return old_value
        except Exception as exc:
            raise ConfigException(f"Config path not found: {path}") from exc

    @classmethod
    def _deep_update(
        cls,
        obj: Mapping,
        updates: Mapping | None,
        create_missing: Union[callable, bool, dict] = True,
    ) -> Mapping:
        """Deep update the 'obj' with the leafs from 'updates

        :param obj: The dict that will be updated
        :param updates: The dict providing the values to update
        :param create_missing: If true, create any missing level.
        :return: the updated 'obj'
        """

        if updates:
            for event in ObjectWalker.objwalk(updates, nodes_only=True):
                data, key = cls._create_missing(
                    obj, event.path, create_missing, replace_path=True
                )
                data[key] = event.value

        return obj

    @classmethod
    def normalize_path(
        cls, path: PathType, *, sep: str = ".", rtn: list = None
    ) -> list:
        """Convert flexible path into normalized Tuple

        'path' is simple: e.g. "a.b.c", "a[1].b", ("a[1]", "b", "c"),
        ["a", "b.c"], ["a.b.c"]

        But also:
        - "a.*.b": match any key
        - "a[*]b": match any index
        - "a..b": recursively match everything

        :param path: the path to identify the element
        :param sep: 'path' separator. Default: '.'
        :return: normalized path
        """
        if rtn is None:
            rtn = []

        if not path:
            return rtn

        pat = re.compile(r"\s*([^\[\]]*)\s*((?:\[\s*(\d+|\*)\s*\]\s*)*)")
        for elem in cls._flatten_and_split_path(path, sep):
            if isinstance(elem, int):
                rtn.append(elem)
                continue
            if isinstance(elem, str):
                match = pat.fullmatch(elem)
                if match:
                    cls._normalize_path_str(match.group(1), match.group(2), rtn)
                    continue

            raise ConfigException(
                f"Invalid config path: Unknown type: '{elem}' in '{path}'"
            )

        cleaned = cls._cleanup_path(rtn)
        if cleaned and cleaned[-1] in [PAT_DEEP, PAT_ANY]:
            raise ConfigException(
                f"Config path must not end with with a selector: '{path}'"
            )

        return cleaned

    @classmethod
    def _normalize_path_str(cls, key, index, rtn: list):
        if key == PAT_ANY:
            rtn.append(PAT_ANY)
        elif not key:
            if not index:
                rtn.append(PAT_DEEP)
        elif key:
            rtn.append(key)

        if index:
            index = index[1:-1]
            index = re.split(r"\s*\]\s*\[\s*", index)
            for cleaned in index:
                if cleaned == PAT_ANY:
                    rtn.append(PAT_ANY)
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
            elif elem not in [PAT_DEEP, PAT_ANY]:
                last = elem
                cleaned.append(elem)
            elif last not in [PAT_DEEP, PAT_ANY]:
                last = elem
                cleaned.append(elem)
            elif last == PAT_DEEP:
                pass
            elif elem == PAT_ANY:
                last = elem
                cleaned.append(elem)
            else:  # last == ANY_INDEX and elem in [RECURSIVE_KEY, ANY_INDEX]
                last = elem
                cleaned.pop()
                cleaned.append(elem)

        return cleaned

    @classmethod
    def get_path(cls, data: Mapping, path: PathType, *, sep: str = ".") -> list:
        """Determine the config path for search patterns such as "c..c32",
        "c.*.c32", "c.c3[*].c32"
        """

        keys = cls.normalize_path(path, sep=sep)
        if not keys:
            return []

        for event in ObjectWalker.objwalk(data, nodes_only=True):
            if cls._match_path(event.path, keys):
                return event.path

        raise ConfigException(f"Invalid config path: '{path}'")

    @classmethod
    def _match_path(cls, path_1: list, path_2: list) -> bool:
        i_1 = 0
        i_2 = 0
        while i_1 < len(path_1):
            elem_1 = path_1[i_1]
            elem_2 = path_2[i_2]
            i_1 += 1

            if elem_2 == PAT_ANY:
                i_2 += 1
                if i_1 < len(path_1) and isinstance(path_1[i_1], int):
                    i_1 += 1
            elif elem_2 == PAT_DEEP:
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

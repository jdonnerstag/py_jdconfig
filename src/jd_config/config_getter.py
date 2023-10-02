#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Assuming a deep Mapping- and Sequence-like structure, walk along
a path and support dict-like get(), set() and delete() operations.
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
    Union,
    Optional,
)

from .string_converter_mixin import StringConverterMixin
from .objwalk import (
    ObjectWalker,
    NodeEvent,
    NewMappingEvent,
    NewSequenceEvent,
    DropContainerEvent,
    NonStrSequence,
)


__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


DEFAULT = object()

PathType: Type = str | int | Iterable[str | int]

WalkResultType: Type = Union[Tuple[Mapping, str], Tuple[Sequence, int]]


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
    """Dict-like get, set, delete and find operations on deep
    Mapping- and Sequence-like structures.
    """

    PAT_ANY_KEY = "*"
    PAT_ANY_IDX = "%"
    PAT_DEEP = ""

    def __init__(self, *, delegator: Optional[callable] = None):
        self.delegator = delegator

    def _invoke_on_missing_handler(self, *args, **kvargs):
        if self.delegator is not None:
            return self.delegator.on_missing_handler(*args, **kvargs)

        return self.on_missing_handler(*args, **kvargs)

    def _flatten_and_split_path(self, path: PathType, sep: str) -> Iterable[str | int]:
        """Flatten a list of list, and further split the str elements by a separator"""

        for elem in flatten(path):
            if isinstance(elem, str):
                for elem_2 in elem.split(sep):
                    yield elem_2
            else:
                yield elem

    def _append_to_path_str(self, path: str, elem: str | int, sep: str = ".") -> str:
        """Convert a element of a normalized path into a string"""

        if isinstance(elem, int):
            path += f"[{str(elem)}]"
        elif elem == self.PAT_ANY_IDX:
            path += "[*]"
        else:
            if path or elem == "":
                path += sep

            path += elem

        return path

    def normalized_path_to_str(self, path: list[str | int], sep: str = ".") -> str:
        """Convert a normalized path into a string"""

        rtn = ""
        for elem in path:
            rtn = self._append_to_path_str(rtn, elem, sep)

        return rtn

    def _walk_path(
        self, data: Mapping | Sequence, path: list[str | int]
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

    def _walk_create_missing(
        self,
        data: Mapping | Sequence,
        path: list[str | int],
        create_missing: Union[callable, bool, Mapping],
        # replace_path: bool = False,
    ) -> WalkResultType:
        """Walk a path to determine the container (Mapping, Sequence) which holds
        the last key. Add missing containers along the way.

        Assume:
        - create_missing = True
        - replace_path = False
        """

        if not path:
            return (data, path)

        last = path[-1]
        for i, key in enumerate(path[0:-1]):
            missing = isinstance(data, Mapping) and key not in data
            missing = missing or (
                not isinstance(data, str)
                and isinstance(data, Sequence)
                and isinstance(key, int)
                and (key < 0 or key >= len(data))
            )

            if missing:
                data[key] = new_data = self.on_missing_handler(
                    data, key, path[0:i], create_missing
                )
                data = new_data
            else:
                data = data[key]

        return (data, last)

    def _walk_replace_path(
        self,
        data: Mapping | Sequence,
        path: list[str | int],
        create_missing: Union[callable, bool, Mapping],
    ) -> WalkResultType:
        """Walk a path to determine the container (Mapping, Sequence) which holds
        the last key. Add missing containers along the way, and replace existing
        elements if they don't have the necessary type.

        Assume:
        - create_missing = True
        - replace_path = True
        """

        if not path:
            return (data, path)

        str_path = ""
        last = path[-1]
        for i, key in enumerate(path[0:-1]):
            str_path = self._append_to_path_str(str_path, key)
            new_data = self.on_missing_handler(data, key, path[0:i], create_missing)
            if isinstance(data[key], type(new_data)):
                data = data[key]
            else:
                data[key] = new_data
                data = new_data

        return (data, last)

    def _walk(
        self,
        data: Mapping | Sequence,
        path: list[str | int],
        create_missing: Union[callable, bool, Mapping],
        replace_path: bool = False,
    ) -> WalkResultType:
        """Walk a path to determine the container (Mapping, Sequence) which holds
        the last key.

        'path' is simple: e.g. "a.b.c", "a[1].b", ("a[1]", "b", "c"),
        ["a", "b.c"], ["a.b.c"]

        :param data: the Mapping like structure
        :param path: a already normalized path
        :param on_missing: an optional bool, callable or dict, which will be
            applied upon missing keys.
        :param replace_path: If true, add missing containers along the way,
            and replace existing elements if they don't have the necessary type.
        :return: The final container and key/index to access the element
        """

        if not path:
            return (data, path)

        if not create_missing and replace_path:
            # TODO Required to support updates ???
            raise ConfigException(
                "Invalid combination: not create_missing and replace_path"
            )

        try:
            if not create_missing and not replace_path:
                data, key = self._walk_path(data, path)
            elif create_missing and not replace_path:
                data, key = self._walk_create_missing(data, path, create_missing)
            elif create_missing and replace_path:
                data, key = self._walk_replace_path(data, path, create_missing)

            if isinstance(data, (Mapping, Sequence)):
                return (data, key)
        except Exception as exc:
            raise ConfigException(f"Failed to find or create path: '{path}'") from exc

        raise ConfigException(
            f"Expect to find a list or dict, but found a value at {path}"
        )

    def _walk_and_find(
        self,
        data: Mapping | Sequence,
        path: list[str | int],
    ) -> WalkResultType:
        """Combine walk() and find() to support extended paths

        Simple examples: "a.b.c", "a[1].b", ("a[1]", "b", "c"),
        ["a", "b.c"], ["a.b.c"]

        But also: "c..c32", "c.c2[*].c32", "c.*.c32"

        :param data: the Mapping like structure
        :param path: a already normalized path
        """

        # Maybe path has pattern like "c..c32", "c.c2[*].c32", "c.*.c32"
        if any(
            x in [self.PAT_DEEP, self.PAT_ANY_KEY, self.PAT_ANY_KEY]
            for x in path
            if isinstance(x, str)
        ):
            deep_path = self._get_path(data, path)
            if deep_path:
                last = deep_path[-1]
                rtn = data
                for elem in deep_path[:-1]:
                    rtn = rtn[elem]

                return (rtn, last)

        # If the path has no find patterns, then walk the path
        try:
            data, key = self._walk(data, path, create_missing=False, replace_path=False)
            return (data, key)
        except Exception as exc:  # pylint: disable=bare-except
            raise ConfigException(f"ConfigDict: Value not found: '{path}'") from exc

    def get(
        self, data: Mapping, path: PathType, default: Any = DEFAULT, *, sep: str = "."
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

        path = self.normalize_path(path, sep=sep)

        try:
            data, key = self._walk_and_find(data, path)
            return data[key]
        except Exception as exc:  # pylint: disable=W0718
            if default != DEFAULT:
                return default

            if isinstance(exc, ConfigException):
                raise

            raise ConfigException(f"ConfigDict: Value not found: '{path}'") from exc

    def _get_old(self, data: Mapping, key: str | int) -> Any:
        try:
            return data[key]
        except (KeyError, TypeError):
            return None

    def delete(
        self,
        data: Mapping | Sequence,
        path: PathType,
        *,
        sep: str = ".",
        exception: bool = True,
    ) -> Any:
        """Similar to 'del dict[key]', but with deep path support"""

        path = self.normalize_path(path, sep=sep)

        try:
            data, key = self._walk_and_find(data, path)
            old_value = self._get_old(data, key)

            del data[key]
            return old_value

        except Exception as exc:  # pylint: disable=broad-exception-caught
            if exception:
                raise ConfigException(f"ConfigDict: Value not found: '{path}'") from exc

        return None

    def on_missing_handler(
        self,
        data: Mapping | Sequence,
        key: str | int,
        path: tuple,
        create_missing: Union[callable, bool, Mapping],
    ) -> Mapping | Sequence:
        """A handler that will be invoked if a path element is missing and
        'create_missing has valid configuration.
        """

        if isinstance(key, int):
            if isinstance(data, Sequence):
                raise ConfigException(f"Can not create missing list entries: '{path}'")

            raise ConfigException(f"Expected a list but found: '{path}' = {type(data)}")

        rtn = None
        if callable(create_missing):
            rtn = create_missing(data, key, path)
        elif isinstance(create_missing, Mapping):
            rtn = create_missing.get(key, None)

            if (rtn is None) and path:
                rtn = create_missing.get(".".join(path + [key]), None)

        # Revert to default
        if rtn is None:
            rtn = {}

        if isinstance(rtn, type):
            return rtn()

        return rtn

    def set(
        self,
        data: Mapping | Sequence,
        path: PathType,
        value: Any,
        *,
        create_missing: Union[callable, bool, Mapping] = False,
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

        path = self.normalize_path(path, sep=sep)
        data, key = self._walk(data, path, create_missing, replace_path)
        old_value = self._get_old(data, key)

        if not replace_value and (key in data):
            raise ConfigException(f"Value already, but replace_value == false: {path}")

        try:
            data[key] = value
            return old_value
        except Exception as exc:
            raise ConfigException(f"Config path not found: {path}") from exc

    def deep_update(self, obj: Mapping, updates: Mapping | None) -> Mapping:
        """Deep update the 'obj' with only the leafs from 'updates'. Create
        missing paths.

        :param obj: The dict that will be updated
        :param updates: The dict providing the values to update
        :param create_missing: If true, create any missing level.
        :return: the updated 'obj'
        """

        if not updates:
            return obj

        stack = [obj]
        any_elem = False
        gen = ObjectWalker.objwalk(updates, nodes_only=False)
        for event in gen:
            cur = stack[-1]

            key = None
            if event.path:
                key = event.path[-1]
                if key.endswith("[*]") and not isinstance(event, NewMappingEvent):
                    raise ConfigException(
                        f"'xyz[*]' syntax requires a value of type mapping: '{event.path}'"
                    )

            if any_elem:
                if not isinstance(cur, NonStrSequence):
                    raise ConfigException(
                        f"'xyz[*]' syntax is only allowed with lists: '{event.path}'"
                    )

                for elem in cur:
                    if isinstance(elem, Mapping) and key in elem:
                        stack.pop()
                        stack.append(elem)
                        cur = elem
                        break
                else:
                    raise ConfigException(f"Element does not exist: '{event.path}'")

                any_elem = False

            if isinstance(event, NewMappingEvent):
                if event.path:
                    if key.endswith("[*]"):
                        key = key[:-3]
                        any_elem = True
                        if not isinstance(cur, Mapping) or (key not in cur):
                            raise ConfigException(
                                "Config element does not exist: '{path}'"
                            )
                    elif (key not in cur) or not isinstance(cur[key], Mapping):
                        cur[key] = event.value
                        if not any_elem:
                            gen.send(True)

                    stack.append(cur[key])
            elif isinstance(event, NewSequenceEvent):
                # TODO List in list?
                key = event.path[-1]
                if (
                    (key not in cur)
                    or not isinstance(cur[key], Sequence)
                    or isinstance(cur[key], str)
                ):
                    cur[key] = event.value
                    gen.send(True)
                stack.append(cur[key])
            elif isinstance(event, NodeEvent):
                key = event.path[-1]
                cur[key] = event.value
            elif isinstance(event, DropContainerEvent):
                stack.pop()

        return obj

    def normalize_path(
        self, path: PathType, *, sep: str = ".", rtn: list = None
    ) -> list:
        """Convert flexible path into normalized Tuple

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
        if rtn is None:
            rtn = []

        if not path:
            return rtn

        pat = re.compile(r"\s*([^\[\]]*)\s*((?:\[\s*(\d+|\*)\s*\]\s*)*)")
        for elem in self._flatten_and_split_path(path, sep):
            if isinstance(elem, int):
                rtn.append(elem)
                continue
            if isinstance(elem, str):
                match = pat.fullmatch(elem)
                if match:
                    self._normalize_path_elem(match.group(1), match.group(2), rtn)
                    continue

            raise ConfigException(
                f"Invalid config path: Unknown type: '{elem}' in '{path}'"
            )

        cleaned = self._cleanup_path(rtn)
        if cleaned and cleaned[-1] in [self.PAT_DEEP, self.PAT_ANY_KEY]:
            raise ConfigException(
                f"Config path must not end with with a selector: '{path}'"
            )

        return cleaned

    def _normalize_path_elem(self, key, index, rtn: list):
        if key == self.PAT_ANY_KEY:
            rtn.append(self.PAT_ANY_KEY)
        elif not key:
            if not index:
                rtn.append(self.PAT_DEEP)
        elif key:
            rtn.append(key)

        if index:
            index = index[1:-1]
            index = re.split(r"\s*\]\s*\[\s*", index)
            for cleaned in index:
                if cleaned == "*":
                    rtn.append(self.PAT_ANY_IDX)
                elif cleaned is not None:
                    rtn.append(int(cleaned))

        return rtn

    def _cleanup_path(self, rtn: list):
        cleaned = []
        last = None
        for elem in rtn:
            if last is None:
                last = elem
                cleaned.append(elem)
            elif elem not in [self.PAT_DEEP, self.PAT_ANY_KEY, self.PAT_ANY_IDX]:
                last = elem
                cleaned.append(elem)
            elif last not in [self.PAT_DEEP, self.PAT_ANY_KEY, self.PAT_ANY_IDX]:
                last = elem
                cleaned.append(elem)
            elif last == self.PAT_DEEP:
                pass
            elif elem in [self.PAT_ANY_KEY, self.PAT_ANY_IDX]:
                last = elem
                cleaned.append(elem)
            else:  # last == ANY_INDEX and elem in [RECURSIVE_KEY, ANY_INDEX]
                last = elem
                cleaned.pop()
                cleaned.append(elem)

        return cleaned

    def _get_path(self, data: Mapping, path: PathType, *, sep: str = ".") -> list:
        """Determine the config path for search patterns such as "c..c32",
        "c.*.c32", "c.c3[*].c32"
        """

        keys = self.normalize_path(path, sep=sep)
        if not keys:
            return []

        for event in ObjectWalker.objwalk(data, nodes_only=True):
            if self._match_path(event.path, keys):
                return event.path

        raise ConfigException(f"Invalid config path: '{path}'")

    def _match_path(self, path_1: list, path_2: list) -> bool:
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

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

from .string_converter_mixin import StringConverterMixin
from .objwalk import objwalk

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


class ConfigException(Exception):
    """Base class for Config Exceptions"""


DEFAULT = object()

PathType: Type = str | Iterable[str]

WalkResultType: Type = Union[Tuple[Mapping, str], Tuple[Sequence, int]]

RECURSIVE_KEY = "__..__"
ANY_INDEX = "__*__"


class ConfigGetter(StringConverterMixin):
    """Dict-like get, set and delete operations on deep Mapping-
    and Sequence-like structures.
    """

    @classmethod
    def walk(
        cls,
        _data: Mapping,
        path: PathType,
        *,
        on_missing: Optional[callable] = None,
        sep: str = ".",
    ) -> WalkResultType:
        """Walk a path to determine the container (Mapping, Sequence) which holds
        the last key.

        'path' is simple: e.g. "a.b.c", "a[1].b", ("a[1]", "b", "c"),
        ["a", "b.c"], ["a.b.c"]

        :param _data: the Mapping like structure
        :param path: the path to identify the element
        :param sep: 'path' separator. Default: '.'
        :return: The final container and key/index to access the element
        """

        keys = cls.normalize_path(path, sep=sep)
        if not keys:
            return _data

        last = keys[-1]
        for i, key in enumerate(keys[0:-1]):
            try:
                _data = _data[key]
            except:  # pylint: disable=bare-except  # noqa: E722
                if callable(on_missing):
                    _data[key] = new_data = on_missing(_data, key, keys[0:i])
                    _data = new_data
                else:
                    raise

        return (_data, last)


    @classmethod
    def get(
        cls, _data: Mapping, path: PathType, default: Any = DEFAULT, *, sep: str = "."
    ) -> Any:
        """Similar to dict.get(), but with deep path support"""

        try:
            _data, key = cls.walk(_data, path, sep=sep)
            return _data[key]
        except Exception:
            pass

        try:
            deep_path = cls.get_path(_data, path)
            rtn = _data
            for elem in deep_path:
                rtn = rtn[elem]
            return rtn
        except Exception as exc:
            if default is not DEFAULT:
                return default

            raise ConfigException(f"ConfigDict: Value not found: '{path}'") from exc


    @classmethod
    def _get_old(cls, _data: Mapping, key: str | int) -> Any:
        try:
            return _data[key]
        except KeyError:
            return None


    @classmethod
    def delete(
        cls, _data: Mapping, path: PathType, *, sep: str = ".", exception: bool = True
    ) -> Any:
        """Similar to 'del dict[key]', but with deep path support"""

        try:
            _data, key = cls.walk(_data, path, sep=sep)
            old_value = cls._get_old(_data, key)

            del _data[key]
            return old_value

        except Exception as exc:  # pylint: disable=broad-exception-caught
            if exception:
                raise ConfigException(f"ConfigDict: Value not found: '{path}'") from exc

        return None


    @classmethod
    def set(
        cls,
        _data: Mapping,
        path: PathType,
        value: Any,
        *,
        create_missing: Union[callable, bool, dict] = False,
        sep: str = ".",
    ) -> Any:
        """Similar to 'dict[key] = valie', but with deep path support.

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
                else:
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

        try:
            _data, key = cls.walk(_data, path, sep=sep, on_missing=on_missing)
            old_value = cls._get_old(_data, key)

            _data[key] = value
            return old_value

        except Exception as exc:
            raise ConfigException(f"ConfigDict: Value not found: '{path}'") from exc


    @classmethod
    def deep_update(
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
        if not updates:
            return obj

        for event in objwalk(updates, nodes_only=True):
            ConfigGetter.set(
                obj, event.path, event.value, create_missing=create_missing
            )

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
        :return: normalized path, with each path segment a tuple element
        """
        if rtn is None:
            rtn = []

        if not path:
            return rtn

        if isinstance(path, str):
            path = path.split(sep)

        for elem in path:
            if isinstance(elem, str):
                sub = elem.split(sep)
                if len(sub) > 1:
                    cls.normalize_path(sub, sep=sep, rtn=rtn)
                    continue

                m = re.fullmatch(r"\s*([^\[\]]*)\s*((?:\[\s*(\d+|\*)\s*\]\s*)*)", elem)
                if m:
                    key = m.group(1)
                    index = m.group(2)

                    if key == "*":
                        rtn.append(ANY_INDEX)
                    elif not key:
                        if not index:
                            rtn.append(RECURSIVE_KEY)
                    elif key:
                        rtn.append(key)

                    if index:
                        index = index[1:-1]
                        index = re.split(r"\s*\]\s*\[\s*", index)
                        for cleaned in index:
                            if cleaned == "*":
                                rtn.append(ANY_INDEX)
                            elif cleaned is not None:
                                rtn.append(int(cleaned))

                    continue

            if isinstance(elem, (list, tuple)):
                cls.normalize_path(elem, sep=sep, rtn=rtn)
                continue

            raise ConfigException(
                f"Invalid config path: Unknown type: '{elem}' in '{path}'"
            )

        cleaned = []
        last = None
        for elem in rtn:
            if last is None:
                last = elem
                cleaned.append(elem)
            elif elem not in [RECURSIVE_KEY, ANY_INDEX]:
                last = elem
                cleaned.append(elem)
            elif last not in [RECURSIVE_KEY, ANY_INDEX]:
                last = elem
                cleaned.append(elem)
            elif last == RECURSIVE_KEY:
                pass
            elif elem == ANY_INDEX:
                last = elem
                cleaned.append(elem)
            else:  # last == ANY_INDEX and elem in [RECURSIVE_KEY, ANY_INDEX]
                last = elem
                cleaned.pop()
                cleaned.append(elem)

        if cleaned and cleaned[-1] in [RECURSIVE_KEY, ANY_INDEX]:
            raise ConfigException(
                f"Config path must not end with with a selector: '{path}'"
            )

        return cleaned


    @classmethod
    def get_path(cls, data: Mapping, path: PathType, *, sep: str = ".") -> list:
        keys = cls.normalize_path(path, sep=sep)
        if not keys:
            return []

        for event in objwalk(data, nodes_only=True):
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

            if elem_2 == ANY_INDEX:  # "__*__"
                i_2 += 1
                if i_1 < len(path_1) and isinstance(path_1[i_1], int):
                    i_1 += 1
            elif elem_2 == RECURSIVE_KEY:  # "__..__"
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

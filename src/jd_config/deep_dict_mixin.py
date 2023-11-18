#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
"""

import logging
from typing import Any, Callable, Mapping, Optional, Self

from jd_config.base_model import BaseModel

from .config_path import CfgPath, PathType
from .utils import DEFAULT, ConfigException, ContainerType, NonStrSequence

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


class DeepDictMixin:
    """Dict-like get, set, delete and find operations on deep
    Mapping- and Sequence-like structures.
    """

    def __init__(
        self,
        data: ContainerType,
        path: Optional[CfgPath] = None,
        *,
        read_only: bool = False,
        **kvargs,
    ) -> None:
        super().__init__(data, path, **kvargs)

        self.read_only = read_only

    def clone(self, data, key) -> Self:
        rtn = super().clone(data, key)
        rtn.read_only = self.read_only
        return rtn

    def check_read_only(self):
        if self.read_only:
            raise KeyError(f"Object instance is read_only: 'path={self.path()}'")

    def delete(self, path: PathType, *, exception: bool = True) -> Any:
        """Similar to 'del dict[key]', but with deep path support"""

        path = self.path_type(path)
        parent_path = self.path_type(path + ("..",))

        try:
            parent = self.get(parent_path)
        except (KeyError, IndexError, TypeError):
            if exception is True:
                raise

            return None

        if not isinstance(parent, BaseModel):
            raise KeyError(f"Expected a ContainerType: '{parent_path}'")

        parent.check_read_only()

        key = path[-1]
        try:
            old_value = parent.get(key)
            if parent.is_mapping():
                del parent.data[key]
            elif parent.is_sequence():
                parent.data.pop(key)
            else:
                raise KeyError(f"Expected a ContainerType: '{parent}'")

        except KeyError:
            if exception is True:
                raise

            old_value = None

        return old_value

    def set(
        self,
        path: PathType,
        value: Any,
        *,
        create_missing: Callable | bool | Mapping = False,
        replace_path: bool = False,
    ) -> Any:
        """Similar to 'dict[key] = value', but with deep path support.

        Limitations:
          - is not possible to append elements to a Sequence. You need to get() the list
            and manually append the element.

        :param path: the path to identify the element
        :param value: the new value
        :param create_missing: what to do if a path element is missing
        :param replace_path: If true, then consider parts missing, of their not containers
        :return: the old value
        """

        path = self.path_type(path)
        if not path:
            raise KeyError("Empty path not allowed for set()")

        parent_path = self.path_type(path + ("..",))

        parent = self.get(
            parent_path,
            create_missing=create_missing,
            replace_path=replace_path,
        )

        if isinstance(parent, BaseModel):
            parent.check_read_only()

            key = path[-1]
            old_value = parent.get(key, default=None, on_missing=False)
            if isinstance(key, str):
                if parent.is_mapping():
                    parent.data[key] = value
                elif replace_path is True:
                    new_value = {key: value}
                    if parent.parent is not None:
                        parent.parent.data[parent_path[-1]] = new_value
                    parent.data = new_value
                else:
                    raise KeyError(
                        f"replace_path == False. Not allowed to change: '{key}'"
                    )
            elif isinstance(key, int):
                if parent.is_sequence():
                    if key == len(parent.data):
                        parent.data.append(value)
                    else:
                        try:
                            parent.data[key] = value
                        except IndexError as exc:
                            raise KeyError(str(exc)) from exc
                elif replace_path is True:
                    new_value = [value]
                    if parent.parent is not None:
                        parent.parent.data[parent_path[-1]] = new_value
                    parent.data = new_value
                else:
                    raise KeyError(
                        f"replace_path == False. Not allowed to change: '{key}'"
                    )
            else:
                raise KeyError(f"Invalid key type (str | int): '{key}'")

            return old_value

        raise KeyError(
            f"Existing elem not a ContainerType, and 'replace_path' == False: '{path}'"
        )

    # @override
    def on_missing(self, data, key, cur_path, exc, **kvargs):
        create_missing = kvargs.get("create_missing", False)
        missing_container = kvargs.get("missing_container", {})
        missing_container_default = kvargs.get("missing_container_default", dict)
        replace_path = kvargs.get("replace_path", False)

        if callable(create_missing):
            return create_missing(data, key, cur_path, exc, **kvargs)
        if isinstance(create_missing, bool) and create_missing is True:
            elem = missing_container_default
            if isinstance(elem, type):
                elem = elem()

            return elem
        if isinstance(create_missing, Mapping):
            elem = create_missing.get(self.path(key), None)
            if elem is None:
                elem = create_missing.get(key, None)
            if elem is None:
                elem = missing_container_default
            if elem is not None:
                if isinstance(elem, type):
                    elem = elem()

                return elem

        super().on_missing(data, key, cur_path, exc, **kvargs)

    def __setitem__(self, key: Any, item: Any) -> None:
        self.set(key, item)

    def __delitem__(self, key: Any) -> None:
        self.delete(key, exception=True)

    # @override
    def get(
        self,
        path: PathType,
        default=DEFAULT,
        *,
        on_missing: Optional[Callable] = None,
        replace_path: bool = False,
        **kvargs,
    ) -> Any:
        value = super().get(
            path, default, on_missing=on_missing, replace_path=replace_path, **kvargs
        )

        if not replace_path:
            return value

        # if replace_path is True, then I know that the path is the parent path,
        # and should be a container
        if isinstance(value, BaseModel):
            return value

        key = path[0]
        value = self.on_missing(self.data, key, self.path(key), None, **kvargs)
        self.data[key] = value
        return super().get(key)

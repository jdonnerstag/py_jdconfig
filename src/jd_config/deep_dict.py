#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
"""

import logging
from typing import Any, Mapping, Sequence, Union
from collections import UserDict
from .config_getter import ConfigGetter, PathType, DEFAULT

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


class DeepDict(UserDict):
    """Dict-like get, set, delete and find operations on deep
    Mapping- and Sequence-like structures.
    """

    def __init__(self, obj: Mapping) -> None:
        super().__init__(obj)
        self.getter = ConfigGetter(delegator=self)

    # pylint: disable=arguments-renamed
    def get(self, path: PathType, default: Any = DEFAULT, *, sep: str = ".") -> Any:
        """Similar to dict.get(), but with deep path support.

        Example paths: "a.b.c", "a[1].b", ("a[1]", "b", "c"),
        ["a", "b.c"], ["a.b.c"]

        And also: "c..c32", "c.c2[*].c32", "c.*.c32"

        :param path: the path to identify the element
        :param sep: 'path' separator. Default: '.'
        :return: The config value
        """

        rtn = self.getter.get(self.data, path, default=default, sep=sep)
        if isinstance(rtn, Mapping):
            return DeepDict(rtn)

        return rtn

    def delete(
        self,
        path: PathType,
        *,
        sep: str = ".",
        exception: bool = True,
    ) -> Any:
        """Similar to 'del dict[key]', but with deep path support"""

        return self.getter.delete(self.data, path, sep=sep, exception=exception)

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

        return self.getter.on_missing_handler(data, key, path, create_missing)

    def set(
        self,
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

        return self.getter.set(
            self.data,
            path,
            value,
            create_missing=create_missing,
            replace_value=replace_value,
            replace_path=replace_path,
            sep=sep,
        )

    def deep_update(
        self,
        updates: Mapping | None
    ) -> Mapping:
        """Deep update the 'obj' with only the leafs from 'updates'. Create
        missing paths.

        :param obj: The dict that will be updated
        :param updates: The dict providing the values to update
        :param create_missing: If true, create any missing level.
        :return: the updated 'obj'
        """

        rtn = self.getter.deep_update(self.data, updates)
        if isinstance(rtn, Mapping):
            return DeepDict(rtn)

        return rtn

    def __getitem__(self, key: Any) -> Any:
        return self.get(key)

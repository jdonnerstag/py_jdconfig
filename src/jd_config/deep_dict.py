#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
"""

import logging
from functools import partial
from typing import Any, Iterator, Mapping, Sequence, Union
from .utils import ConfigException, PathType, DEFAULT
from .deep_getter_with_search_and_resolver import ConfigResolvePlugin
from .deep_update import DeepUpdateMixin
from .deep_getter_base import GetterContext

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


class DeepDict(Mapping, DeepUpdateMixin):
    """Dict-like get, set, delete and find operations on deep
    Mapping- and Sequence-like structures.
    """

    def __init__(self, obj: Mapping, path: PathType = ()) -> None:
        self.obj = obj
        self.getter = ConfigResolvePlugin(data=obj, path=path)

    # pylint: disable=arguments-renamed
    def get(self, path: PathType, default: Any = DEFAULT) -> Any:
        """Similar to dict.get(), but with deep path support.

        Example paths: "a.b.c", "a[1].b", ("a[1]", "b", "c"),
        ["a", "b.c"], ["a.b.c"]

        And also: "c..c32", "c.c2[*].c32", "c.*.c32"

        :param path: the path to identify the element
        :param sep: 'path' separator. Default: '.'
        :return: The config value
        """

        rtn = self.getter.get(path, default=default)
        return rtn

    def delete(
        self,
        path: PathType,
        *,
        exception: bool = True,
    ) -> Any:
        """Similar to 'del dict[key]', but with deep path support"""

        try:
            data, path = self.getter.find(path, create_missing=False)
            key = path[-1]
            del data[key]
        except (KeyError, IndexError, ConfigException):
            if exception:
                raise

    def on_missing_handler(
        self,
        ctx: GetterContext,
        exc: Exception,
        *,
        missing_container_default=None,
        missing_container=None,
    ) -> Mapping | Sequence:
        """A handler that will be invoked if a path element is missing and
        'create_missing has valid configuration.
        """

        elem = None
        if missing_container:
            elem = missing_container.get(ctx.cur_path(), None)
            if elem is None:
                elem = missing_container.get(ctx.key, None)
        if elem is None:
            elem = missing_container_default
        if elem is None:
            return self.getter.on_missing(ctx, exc)

        if isinstance(elem, type):
            elem = elem()

        ctx.data[ctx.key] = elem
        return elem

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

        path = self.getter.normalize_path(path)
        if not path:
            raise ConfigException("Empty path not allowed for set()")

        on_missing = None
        if callable(create_missing):
            on_missing = create_missing
        elif isinstance(create_missing, bool) and create_missing is True:
            on_missing = partial(
                self.on_missing_handler, missing_container_default=dict
            )
        elif isinstance(create_missing, Mapping):
            on_missing = partial(
                self.on_missing_handler,
                missing_container_default=dict,
                missing_container=create_missing,
            )

        args = None
        if replace_path:
            args = {"cb_get_2_with_context": replace_path}

        key = path[-1]
        path = path[:-1]
        data = self.getter.get(path, on_missing=on_missing, args=args)

        old_value = None
        try:
            old_value = data[key]
        except:  # pylint: disable=bare-except
            pass

        data[key] = value

        return old_value

    def __getitem__(self, key: Any) -> Any:
        return self.get(key)

    def __setitem__(self, key: Any, item: Any) -> None:
        self.set(key, item)

    def __len__(self) -> int:
        return self.obj.__len__()

    def __iter__(self) -> Iterator:
        return self.obj.__iter__()

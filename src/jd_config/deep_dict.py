#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
"""

import logging
from functools import partial
from typing import Any, Callable, Iterator, Mapping, Optional, Sequence, Type, Union

from jd_config.deep_getter_with_search import ConfigSearchMixin
from .utils import ConfigException, ContainerType, NonStrSequence, PathType, DEFAULT
from .deep_getter_with_search_and_resolver import ConfigResolveMixin
from .deep_update import DeepUpdateMixin
from .deep_getter_base import DeepGetter, GetterContext

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


# Note: the order of the subclasses is relevant !!!
class DefaultConfigGetter(ConfigSearchMixin, ConfigResolveMixin, DeepGetter):
    """Default Deep Container Getter for Configs"""

    def __init__(
        self,
        data: Mapping | NonStrSequence,
        path: PathType,
        *,
        on_missing: Optional[Callable] = None,
        _memo: list | None = None,
    ) -> None:
        DeepGetter.__init__(self, data, path, on_missing=on_missing, _memo=_memo)
        ConfigResolveMixin.__init__(self)
        ConfigSearchMixin.__init__(self)


class DeepDict(Mapping, DeepUpdateMixin):
    """Dict-like get, set, delete and find operations on deep
    Mapping- and Sequence-like structures.
    """

    def __init__(
        self, obj: Mapping, path: PathType = (), getter: Optional[DeepGetter] = None
    ) -> None:
        self.obj = obj
        self.getter = self.new_getter(obj, path) if getter is None else getter

    def new_getter(self, obj: Mapping, path: PathType) -> DeepGetter:
        """Create a new Getter. Subclasses may provide their own."""
        return DefaultConfigGetter(obj, path, on_missing=self.on_missing)

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

    def delete(self, path: PathType, *, exception: bool = True) -> Any:
        """Similar to 'del dict[key]', but with deep path support"""

        path = self.getter.normalize_path(path)
        assert path
        key, path = path[-1], path[:-1]

        old_data = None
        data = None
        try:
            data = self.getter.get(path)
        except (KeyError, IndexError, ConfigException):
            if exception:
                raise

            return old_data

        if data is not None:
            old_data = data[key]

        del data[key]
        return old_data

    def on_missing(
        self,
        ctx: GetterContext,
        exc: Exception,
        *,
        missing_container_default=None,
        missing_container=None,
    ) -> Any:
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
            return self.getter.on_missing_default(ctx, exc)

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
        replace_path: bool = False,
    ) -> Any:
        """Similar to 'dict[key] = value', but with deep path support.

        Limitations:
          - is not possible to append elements to a Sequence. You need to get() the list
            and manually append the element.

        :param data: the Mapping like structure
        :param path: the path to identify the element
        :param value: the new value
        :param create_missing: what to do if a path element is missing
        :param replace_path: If true, then consider parts missing, of their not containers
        :param sep: 'path' separator. Default: '.'
        """

        path = self.getter.normalize_path(path)
        if not path:
            raise ConfigException("Empty path not allowed for set()")

        ctx = self.getter.new_context(data=self.obj)

        raise_exc = False
        last_parent = None
        old_value = None
        for ctx in self.getter.walk_path(ctx, path):
            try:
                last_parent = ctx.data
                ctx.data = self.getter.cb_get_2_with_context(ctx)
                old_value = ctx.data

                if (ctx.idx + 1) < len(ctx.path):
                    next_key = ctx.path[ctx.idx + 1]
                    expected_container_type = None
                    if isinstance(next_key, str):
                        expected_container_type = Mapping
                    elif isinstance(next_key, int):
                        expected_container_type = NonStrSequence

                    if not isinstance(ctx.data, expected_container_type):
                        if replace_path:
                            ctx.data = last_parent
                            ctx.data = self._on_missing(ctx, None, create_missing)
                        else:
                            raise_exc = True
                            break

            except (KeyError, IndexError, ConfigException) as exc:
                if (ctx.idx + 1) < len(ctx.path):
                    ctx.data = self._on_missing(ctx, exc, create_missing)
                else:
                    old_value = None

        if raise_exc:
            raise ConfigException(
                "Unable to replace existing value. Consider using 'replace_path=True':"
                f" '{ctx.cur_path()}'"
            )

        last_parent[ctx.key] = value

        return old_value

    def _on_missing(self, ctx, exc, create_missing):
        if callable(create_missing):
            return create_missing(ctx, exc)
        if isinstance(create_missing, bool) and create_missing is True:
            return self.on_missing(ctx, exc, missing_container_default=dict)
        if isinstance(create_missing, Mapping):
            return self.on_missing(
                ctx,
                exc,
                missing_container_default=dict,
                missing_container=create_missing,
            )

        raise ConfigException(
            f"Unable to add missing value for: '{ctx.cur_path()}'"
        ) from exc

    def __getitem__(self, key: Any) -> Any:
        return self.get(key)

    def __setitem__(self, key: Any, item: Any) -> None:
        self.set(key, item)

    def __len__(self) -> int:
        return self.obj.__len__()

    def __iter__(self) -> Iterator:
        return self.obj.__iter__()

#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
"""

import logging
from typing import Any, Callable, Iterator, Mapping, Optional, Union

from .deep_export_mixin import DeepExportMixin
from .deep_getter_base import DeepGetter, GetterContext
from .deep_getter_with_search import ConfigSearchMixin
from .deep_getter_with_search_and_resolver import ConfigResolveMixin
from .deep_update import DeepUpdateMixin
from .utils import DEFAULT, ConfigException, ContainerType, NonStrSequence, PathType
from .value_reader import ValueReader

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


class DeepDictMixin:
    """..."""

    def cb_get(self, data, key, ctx: GetterContext) -> Any:
        """Avoid recursive resolving ..."""
        if isinstance(data, DeepDict):
            data = data.obj

        return super().cb_get(data, key, ctx)


# Note: the order of the subclasses is relevant !!!
class DefaultConfigGetter(
    DeepExportMixin, ConfigSearchMixin, ConfigResolveMixin, DeepDictMixin, DeepGetter
):
    """Default Deep Container Getter for Configs"""

    def __init__(
        self,
        *,
        value_reader: Optional[ValueReader] = None,
        on_missing: Optional[Callable] = None,
    ) -> None:
        DeepGetter.__init__(self, on_missing=on_missing)
        DeepDictMixin.__init__(self)
        ConfigResolveMixin.__init__(self, value_reader)
        ConfigSearchMixin.__init__(self)
        DeepExportMixin.__init__(self)


class DeepDict(Mapping, DeepUpdateMixin):
    """Dict-like get, set, delete and find operations on deep
    Mapping- and Sequence-like structures.
    """

    def __init__(
        self,
        obj: Mapping,
        root: Optional[Mapping] = None,
        path: Optional[PathType] = None,
        getter: Optional[DeepGetter] = None,
    ) -> None:
        self.getter = self.new_getter() if getter is None else getter
        self.obj = obj
        self.root = obj if root is None else root
        self.path = () if path is None else self.getter.normalize_path(path)

        DeepUpdateMixin.__init__(self)

    def new_getter(self) -> DeepGetter:
        """Create a new Getter. Subclasses may provide their own."""
        return DefaultConfigGetter(on_missing=self.on_missing)

    def register_placeholder_handler(self, name: str, type_: type) -> None:
        """Register (add or replace) a placeholder handler"""

        self.getter.value_reader.registry[name] = type_

    # pylint: disable=arguments-renamed
    def get(self, path: PathType, default: Any = DEFAULT, resolve: bool = True) -> Any:
        """Similar to dict.get(), but with deep path support.

        Example paths: "a.b.c", "a[1].b", ("a[1]", "b", "c"),
        ["a", "b.c"], ["a.b.c"]

        And also: "c..c32", "c.c2[*].c32", "c.*.c32"

        :param path: the path to identify the element
        :param sep: 'path' separator. Default: '.'
        :return: The config value
        """

        getter = self.getter
        ctx = getter.new_context(self.obj, root=self.root, skip_resolver=not resolve)
        path = getter.normalize_path(path)
        rtn = getter.get(self.obj, path, default=default, ctx=ctx)
        if isinstance(rtn, ContainerType):
            rtn = DeepDict(rtn, self.root, self.path + path, self.getter)

        return rtn

    def delete(self, path: PathType, *, exception: bool = True) -> Any:
        """Similar to 'del dict[key]', but with deep path support"""

        path = self.getter.normalize_path(path)
        assert path
        key, path = path[-1], path[:-1]

        old_data = None
        try:
            data = self.getter.get(self.obj, path)

            try:
                old_data = data[key]
            except:  # pylint: disable=bare-except
                pass

            if isinstance(data, Mapping) and isinstance(key, str):
                del data[key]
            elif isinstance(data, NonStrSequence) and isinstance(key, int):
                data.pop(key)
            else:
                raise ConfigException(
                    f"Don't know how to delete elem: '{key}' from '{path}'"
                )

        except (KeyError, IndexError, ConfigException):
            if exception:
                raise

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
                ctx.data = self.getter.cb_get(ctx.data, ctx.key, ctx)
                old_value = ctx.data

                if (ctx.idx + 1) < len(ctx.path):
                    next_key = ctx.path[ctx.idx + 1]
                    missing_container = None
                    if isinstance(next_key, str):
                        replace = not isinstance(ctx.data, Mapping)
                        missing_container = dict
                    elif isinstance(next_key, int):
                        replace = not isinstance(ctx.data, NonStrSequence)
                        missing_container = list

                    if replace:
                        if replace_path:
                            ctx.data = last_parent
                            ctx.data = self._on_missing(
                                ctx, None, create_missing, missing_container
                            )
                        else:
                            raise_exc = True
                            break

            except (KeyError, IndexError, ConfigException) as exc:
                if (ctx.idx + 1) < len(ctx.path):
                    ctx.data = self._on_missing(ctx, exc, create_missing, dict)
                else:
                    old_value = None

        if raise_exc:
            raise ConfigException(
                "Unable to replace existing value. Consider using 'replace_path=True':"
                f" '{ctx.cur_path()}'"
            )

        # Append if it is a list, and index == list size
        if (
            isinstance(last_parent, NonStrSequence)
            and isinstance(ctx.key, int)
            and ctx.key == len(last_parent)
        ):
            last_parent.append(value)
        else:
            last_parent[ctx.key] = value

        return old_value

    def _on_missing(self, ctx, exc, create_missing, missing_container):
        if callable(create_missing):
            return create_missing(ctx, exc)
        if isinstance(create_missing, bool) and create_missing is True:
            return self.on_missing(
                ctx, exc, missing_container_default=missing_container
            )
        if isinstance(create_missing, Mapping):
            return self.on_missing(
                ctx,
                exc,
                missing_container_default=missing_container,
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

    def __eq__(self, other: Mapping) -> bool:
        return self.obj == other

    def __repr__(self) -> str:
        return self.obj.__repr__()

    def __str__(self) -> str:
        return self.obj.__str__()

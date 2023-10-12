#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
An expandable base class to retrieve (get) elements in deep container structures,
e.g. Mapping and NonStrSequence.

Either the base class or a subclass should support:
- Support for any container type, that can hold 0-N values (e.g. Mapping, Sequence)
- Options to handle missing elements when walking the path. Default is to raise an
  exception. But it should also be possible automatically add the missing elements.
  Whatever type they may require.
- Optionally, but not strictly required, register the new object with the parent.
- Support path search patterns, e.g. "a..c", "a.*.c", "a.b[*].c"
- Support ways to evaluate the values retrieved, e.g. `{ref:a}`, and return what
  it evaluates to (replacing the original value).
- In deep update scenarios it must be possible to replace existing nodes. E.g.
  replace an existing int or string value, with a dict or list.
"""

import logging
from typing import Any, Iterator, Mapping, Optional, Callable

from .dict_list import DictList
from .utils import NonStrSequence, PathType, ConfigException, DEFAULT
from .config_path import ConfigPath

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


GetterPlugin = Callable[["GetterContext", Any, int], Any]


class GetterContext:
    """The current context while walking a deep structure"""

    def __init__(
        self,
        data: Mapping | NonStrSequence,
        on_missing: Optional[callable] = None,
        on_get_with_context: Optional[list[callable]] = None,
        _memo: Optional[list] = None,
    ) -> None:
        # Current parent container
        self.data = data

        # Current key to retrieve the element from the parent
        # Note that 'key' may not be 'path[idx]'
        self.key: str | int | None = None

        # Normalized path as provided by the user
        self.path: tuple[str | int] = ()

        # While walking, the current index within the path
        self.idx: int = 0

        self.on_missing: callable = on_missing

        self.on_get_with_context: Optional[list[GetterPlugin]] = on_get_with_context

        # internal: detect recursions
        self._memo: list = [] if _memo is None else _memo

    @property
    def value(self) -> Any:
        """Given the current 'key', get the value from the underlying container"""
        return self.data[self.key]

    def cur_path(self) -> tuple[str | int]:
        """While walking, the path to the current parent element"""
        return self.path[: self.idx] + (self.key,)

    def path_replace(self, replace, count=1) -> tuple:
        """Replace the path element(s) at the current position (idx), with
        the new ones provided.
        """
        if not isinstance(replace, tuple):
            replace = (replace,)

        return self.path[: self.idx] + replace + self.path[self.idx + count :]

    def invoke_next(self, value: Any, idx: int) -> Any:
        if idx < 0:
            idx = len(self.on_get_with_context) + idx

        assert idx >= 0

        plugin = self.on_get_with_context[idx]
        return plugin(self, value, idx - 1)


class DeepGetter:
    """Getter for deep container structures (Mapping and NonStrSequence)"""

    def __init__(
        self, data: Mapping | NonStrSequence, path: PathType, *, _memo=None
    ) -> None:
        self._data = data
        self._path = path  # TODO used anywhere?
        self._memo = _memo  # TODO used anywhere?

        self.on_missing_default: callable = self.on_missing
        self.on_get_default: callable = self.cb_get
        self.on_get_with_context_default: list[GetterPlugin] = [
            self.cb_get_2_with_context
        ]

    def cb_get(self, data, key, path) -> Any:
        """Retrieve an element from its parent container.

        Subclasses may extend it, e.g. to resolve the value `{ref:a}`,
        before return the value.

        :param data: the parent container
        :param key: the key to access the element in the parent container
        :param path: `path` to the parent element
        :return: the value representing the element in the parent container
        """
        return data[key]

    def cb_get_2_with_context(self, ctx: GetterContext, _value: Any, _idx: int) -> Any:
        """Retrieve an element from its parent container.

        Sometimes more flexibility is required. E.g. deep search pattern (e.g. `a..c`)
        must be able to modify the context and modify the `path` or index (idx).

        :param ctx: a mutable context
        :return: the value representing the element in the parent container
        """
        return self.cb_get(ctx.data, ctx.key, ctx.cur_path())

    def on_missing(self, ctx: GetterContext) -> Any:
        """Default behavior if an element along the path is missing.
        => Re-raise the exception.
        """
        raise ConfigException(f"Config not found: {ctx.cur_path()}")

    def normalize_path(self, path: PathType) -> tuple[str | int]:
        """Normalize a path. See `ConfigPath`for details."""

        # TODO Need a version without search pattern support
        return tuple(ConfigPath.normalize_path(path))

    def get_path(
        self, path: PathType, ctx: Optional[GetterContext] = None
    ) -> list[str | int]:
        """Determine the real path.

        The base implementation just returns the normalized path, without
        validating, that the elements exist.

        Subclasses may extend the behavior and provide searching, e.g. `a..c`,
        `a.*.c`, `a.b[*].c`, etc.. Returning the path to the element found.

        :param path: A user provided (config) path like object, e.g. `a.b[2].c`
        :return: the normalized path
        """

        # pylint: disable=redefined-argument-from-local
        for ctx in self.walk_path(path, ctx):
            data = DictList(ctx.data)
            if ctx.key not in data:
                raise ConfigException(f"Config not found for: '{ctx.cur_path()}'")

        return ctx.path

    def get(
        self,
        path: PathType,
        default: Any = DEFAULT,
        *,
        ctx: Optional[GetterContext] = None,
    ) -> Any:
        """The main entry point: walk the provided path and return whatever the
        value at that end of that path will be.

        :param path: A user provided (config) path like object, e.g. `a.b[2].c`
        :param default: Optional default value, if the value was not found
        :param _memo: Used to detect recursions when resolving values, e.g. `{ref:a}`
        """

        value = None

        # pylint: disable=redefined-argument-from-local
        for ctx in self.walk_path(path, ctx):
            data = DictList(ctx.data)
            if ctx.key in data:
                value = self.cb_get_2_with_context(ctx, value, -1)
            else:
                if default is not DEFAULT:
                    return default

                if callable(ctx.on_missing):
                    value = ctx.on_missing(ctx)
                else:
                    value = self.on_missing(ctx)

        return value

    def walk_path(
        self, path: PathType, ctx: Optional[GetterContext] = None
    ) -> Iterator[GetterContext]:
        """Walk the path and yield the current context.

        1) For search patterns (e.g. "a..c") to work, the 'path' and 'idx'
           can be modified
        2) For search patterns (e.g. "a..c") to work, we do not retrieve the value.
           '*' or '..' are not valid keys. Property ctx.value can be used to lazy
           retrieve the value easily
        """

        if ctx is None:
            ctx = GetterContext(self._data)

        ctx.path = self.normalize_path(path)
        if not ctx.path:
            return

        try:
            while ctx.idx < len(ctx.path):
                ctx.key = ctx.path[ctx.idx]
                yield ctx
                ctx.data = ctx.data[ctx.key]
                ctx.idx += 1
        except (KeyError, IndexError) as exc:
            raise ConfigException(f"Config not found: '{ctx.cur_path()}'") from exc

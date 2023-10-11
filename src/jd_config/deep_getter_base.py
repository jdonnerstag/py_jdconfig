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
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Sequence, Callable

from .utils import NonStrSequence, PathType, ConfigException, DEFAULT
from .config_path import ConfigPath

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


GetterPlugin: type = Callable[["GetterContext", Any, int], Any]


@dataclass
class GetterContext:
    """The current context while walking a deep structure"""

    # Current parent container
    data: Mapping | NonStrSequence

    # Current key to retrieve the element from the parent
    key: str | int

    # Normalized path as provided by the user
    path: tuple[str | int]

    # While walking, the current index within the path
    idx: int

    on_get: callable

    on_get_with_context: list[GetterPlugin]

    on_missing: callable

    getter: "DeepGetter"

    # internal: detect recursions
    memo: list = field(default_factory=list)

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

    def get(self, path: PathType, default: Any = DEFAULT, *, _memo=None):
        return self.getter(
            path,
            default,
            _memo=_memo,
            on_missing=self.on_missing,
            on_get_with_context=self.on_get_with_context,
        )


class DeepGetter:
    """Getter for deep container structures (Mapping and NonStrSequence)"""

    def __init__(
        self, data: Mapping | NonStrSequence, path: PathType, *, _memo=None
    ) -> None:
        self._data = data
        self._path = path  # TODO used anywhere?
        self._memo = _memo  # TODO used anywhere?

        self.on_get_default: callable = self.cb_get
        self.on_get_with_context_default: list[GetterPlugin] = [
            self.cb_get_2_with_context
        ]
        self.on_missing_default: callable = self.on_missing

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
        return ctx.on_get(ctx.data, ctx.key, ctx.cur_path())

    def cb_get_3_with_missing(self, ctx: GetterContext) -> Any:
        """A wrapper around lower level getters to catch exception and
        invoke an `on_missing()` handler.

        :param ctx: a mutable context
        :return: the value representing the element in the parent container
        """
        try:
            return ctx.invoke_next(None, -1)
        except (KeyError, IndexError) as exc:
            rtn = ctx.on_missing(ctx, exc)
            return rtn

    def on_missing(self, ctx: GetterContext, exc) -> Any:
        """Default behavior if an element along the path is missing.
        => Re-raise the exception.
        """
        raise exc

    def normalize_path(self, path: PathType) -> tuple[str | int]:
        """Normalize a path. See `ConfigPath`for details."""

        # TODO Need a version without search pattern support
        return tuple(ConfigPath.normalize_path(path))

    def get_path(self, path: PathType) -> list[str | int]:
        """Determine the real path.

        The base implementation just returns the normalized path, without
        validating, that the elements exist.

        Subclasses may extend the behavior and provide searching, e.g. `a..c`,
        `a.*.c`, `a.b[*].c`, etc.. Returning the path to the element found.

        :param path: A user provided (config) path like object, e.g. `a.b[2].c`
        :return: the normalized path
        """

        ctx = self.get_ctx(path)
        return ctx.path

    def new_context(self, data, path, _memo) -> GetterContext:
        """Create a new context. Allow subclasses to provide an extended version"""
        return GetterContext(
            data,
            path[0],
            path,
            0,
            self.on_get_default,  # Apply pre-configured default values
            self.on_get_with_context_default,
            self.on_missing_default,
            self,
            _memo,
        )

    def get(
        self,
        path: PathType,
        default: Any = DEFAULT,
        *,
        on_missing: Optional[callable] = None,
        on_get_with_context: Optional[list[GetterPlugin]] = None,
        _memo: list = None,
    ) -> Any:
        """The main entry point: walk the provided path and return whatever the
        value at that end of that path will be.

        :param path: A user provided (config) path like object, e.g. `a.b[2].c`
        :param default: Optional default value, if the value was not found
        :param _memo: Used to detect recursions when resolving values, e.g. `{ref:a}`
        """

        try:
            ctx = self.get_ctx(
                path,
                on_missing=on_missing,
                on_get_with_context=on_get_with_context,
                _memo=_memo,
            )
            return ctx.data
        except ConfigException:
            if default is not DEFAULT:
                return default

            raise

    def get_ctx(
        self,
        path: PathType,
        *,
        on_missing: Optional[callable] = None,
        on_get_with_context: Optional[list[GetterPlugin]] = None,
        _memo: list = None,
    ) -> GetterContext:
        """The main entry point: walk the provided path and return whatever the
        value at that end of that path will be.

        :param path: A user provided (config) path like object, e.g. `a.b[2].c`
        :param default: Optional default value, if the value was not found
        :param _memo: Used to detect recursions when resolving values, e.g. `{ref:a}`
        """

        path = self.normalize_path(path)
        if not path:
            return self._data

        ctx = self.new_context(self._data, path, _memo)

        if callable(on_missing):
            ctx.on_missing = on_missing

        if isinstance(on_get_with_context, Sequence) and on_get_with_context:
            ctx.on_get_with_context = on_get_with_context

        try:
            ctx = self.walk_path(ctx)
            return ctx
        except (KeyError, IndexError) as exc:
            raise ConfigException(f"Config not found: '{ctx.cur_path()}'") from exc

    def walk_path(self, ctx: GetterContext) -> GetterContext:
        """Walk the path and invoke the handlers for every element along
        the way
        """

        while ctx.idx < len(ctx.path):
            ctx.key = ctx.path[ctx.idx]
            ctx.data = self.cb_get_3_with_missing(ctx)
            ctx.idx += 1

        return ctx

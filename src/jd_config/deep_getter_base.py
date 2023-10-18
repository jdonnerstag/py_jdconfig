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
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterator, Optional

from .config_path import ConfigPath
from .placeholders import Placeholder
from .utils import DEFAULT, ConfigException, ContainerType, PathType

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


# pylint: disable=too-many-instance-attributes
@dataclass
class GetterContext:
    """The current context while walking a deep structure"""

    # Current parent container
    data: ContainerType

    # Current key to retrieve the element from the parent
    # Note that 'key' may not be 'path[idx]'
    key: str | int | None = None

    # Normalized full path as provided by the user
    path: tuple[str | int] = ()

    # While walking, the current index within the path
    idx: int = 0

    on_missing: Optional[Callable] = None

    # The root object of the yaml or json file, required for resolving
    # placeholders
    root: Optional[ContainerType] = None

    file_imports: Optional[list[Path]] = None

    # I'm not a fan of dynamically adding attributes to a class.
    # Arbitrary attribute which extensions may require.
    args: Optional[dict] = None

    # internal: detect recursions
    memo: Optional[list] = None

    def __post_init__(self) -> None:
        if self.root is None:
            self.root = self.data

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

    def add_memo(self, placeholder: Placeholder) -> None:
        """Identify recursions"""

        if self.memo is None:
            self.memo = []

        if placeholder in self.memo:
            self.memo.append(placeholder)
            raise RecursionError(f"Config recursion detected: {self.memo}")

        self.memo.append(placeholder)


class DeepGetter:
    """Getter for deep container structures (Mapping and NonStrSequence)"""

    def __init__(self, *, on_missing: Optional[Callable] = None) -> None:
        self.on_missing = self.on_missing_default
        if callable(on_missing):
            self.on_missing = on_missing

    def new_context(
        self,
        data: ContainerType,
        *,
        on_missing: Optional[Callable] = None,
        _memo: Optional[list] = None,
        root: Optional[ContainerType] = None,
        **kvargs,
    ) -> GetterContext:
        """Assign a new context to the getter, optionally providing
        `on_missing` and `getter` overrides
        """

        if not callable(on_missing):
            on_missing = self.on_missing

        return GetterContext(
            data, root=root, on_missing=on_missing, memo=_memo, args=kvargs
        )

    def cb_get(self, data, key, ctx: GetterContext, **kvargs) -> Any:
        """Retrieve an element from its parent container.

        Subclasses may extend it, e.g. to resolve the value `{ref:a}`,
        before return the value.

        :param data: the parent container
        :param key: the key to access the element in the parent container
        :param ctx: the context, if needed
        :return: the value representing the element in the parent container
        """
        return data[key]

    def on_missing_default(self, ctx: GetterContext, exc: Exception) -> Any:
        """Default behavior if an element along the path is missing.
        => Re-raise the exception.
        """
        raise ConfigException(f"Config not found: {ctx.cur_path()}")

    def normalize_path(self, path: PathType) -> tuple[str | int]:
        """Normalize a path. See `ConfigPath`for details."""

        # TODO Need a version without search pattern support
        return tuple(ConfigPath.normalize_path(path))

    def get_path(self, data: ContainerType, path: PathType) -> list[str | int]:
        """Determine the real path.

        The base implementation just returns the normalized path, without
        validating, that the elements exist.

        Subclasses may extend the behavior and provide searching, e.g. `a..c`,
        `a.*.c`, `a.b[*].c`, etc.. Returning the path to the element found.

        :param path: A user provided (config) path like object, e.g. `a.b[2].c`
        :return: the normalized path
        """

        ctx = self.new_context(data)

        try:
            for ctx in self.walk_path(ctx, path):
                ctx.data = self.cb_get(ctx.data, ctx.key, ctx)
        except (KeyError, IndexError) as exc:
            raise ConfigException(f"Config not found: '{ctx.cur_path()}'") from exc

        return ctx.path

    def get(
        self,
        data: ContainerType,
        path: PathType,
        default: Any = DEFAULT,
        *,
        on_missing: Optional[Callable] = None,
        ctx: Optional[GetterContext] = None,
        _memo: Optional[list] = None,
    ) -> Any:
        """The main entry point: walk the provided path and return whatever the
        value at that end of that path will be.

        :param path: A user provided (config) path like object, e.g. `a.b[2].c`
        :param default: Optional default value, if the value was not found
        :param _memo: Used to detect recursions when resolving values, e.g. `{ref:a}`
        """

        if ctx is None:
            ctx = self.new_context(data, _memo=_memo)
        else:
            ctx.data = data
            if _memo is not None:
                ctx.memo = _memo

        # pylint: disable=redefined-argument-from-local
        for ctx in self.walk_path(ctx, path):
            try:
                ctx.data = self.cb_get(ctx.data, ctx.key, ctx)
            except (KeyError, IndexError, ConfigException) as exc:
                if default is not DEFAULT:
                    return default

                if callable(on_missing):
                    ctx.data = on_missing(ctx, exc)
                elif callable(ctx.on_missing):
                    ctx.data = ctx.on_missing(ctx, exc)
                else:
                    ctx.data = self.on_missing(ctx, exc)

                if not isinstance(ctx.data, ContainerType):
                    return ctx.data

        # pylint: disable=undefined-loop-variable
        return ctx.data

    def walk_path(self, ctx: GetterContext, path: PathType) -> Iterator[GetterContext]:
        """Walk the path and yield the current context.

        1) For search patterns (e.g. "a..c") to work, the 'path' and 'idx'
           can be modified
        2) For search patterns (e.g. "a..c") to work, we do not retrieve the value.
           '*' or '..' are not valid keys. Property ctx.value can be used to lazy
           retrieve the value easily
        """

        ctx.path = self.normalize_path(path)
        if not ctx.path:
            return

        try:
            ctx.idx = 0
            while ctx.idx < len(ctx.path):
                ctx.key = ctx.path[ctx.idx]
                yield ctx
                ctx.idx += 1
        except (KeyError, IndexError) as exc:
            raise ConfigException(f"Config not found: '{ctx.cur_path()}'") from exc

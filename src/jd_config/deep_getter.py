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
from typing import Any, Callable, Iterator, Optional

from .config_path import CfgPath, PathType
from .file_loader import ConfigFile
from .placeholders import Placeholder, new_trace
from .utils import DEFAULT, ConfigException, ContainerType, relative_to_cwd

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


OnMissing = Callable[["GetterContext", Exception], Any]


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
    path: CfgPath = field(default_factory=CfgPath)

    # While walking, the current index within the path
    idx: int = 0

    # Callback function if key could not be found
    on_missing: Optional[OnMissing] = None

    # While walking, the yaml file associated with the container
    current_file: Optional[ContainerType] = None

    # The global (main) yaml file
    global_file: Optional[ContainerType] = None

    # I'm not a fan of dynamically adding attributes to a class.
    # Arbitrary attributes which extensions may require.
    args: Optional[dict] = None

    # internal: detect recursions
    memo: Optional[list] = None

    def __post_init__(self) -> None:
        if self.current_file is None:
            self.current_file = self.data

        if self.global_file is None:
            self.global_file = self.current_file

    @property
    def value(self) -> Any:
        """Given the current 'key', get the value from the underlying container"""
        return self.data[self.key]

    def cur_path(self) -> CfgPath:
        """While walking, the path to the current parent element"""
        return type(self.path)(self.path[: self.idx] + (self.key,))

    def parent_path(self, offset: int) -> CfgPath:
        """While walking, the path to the current parent element"""
        return type(self.path)(self.path[: self.idx - offset])

    def path_replace(self, replace, count=1) -> CfgPath:
        """Replace the path element(s) at the current position (idx), with
        the new ones provided.
        """
        if isinstance(replace, CfgPath):
            replace = replace.path

        if not isinstance(replace, tuple):
            replace = (replace,)

        return type(self.path)(
            self.path[: self.idx] + replace + self.path[self.idx + count :]
        )

    def add_memo(self, placeholder: Placeholder) -> None:
        """Identify recursions"""

        if self.memo is None:
            self.memo = []

        if placeholder in self.memo:
            self.memo.append(placeholder)
            raise ConfigException(f"Config recursion detected: {self.memo}")

        self.memo.append(placeholder)


class DeepGetter:
    """Getter for deep container structures (Mapping and NonStrSequence).

    This is one of the core classes of the config package. It works in close
    collaboration with GetterContext to provide the extensability and
    flexibility we need.
    """

    def __init__(self, *, on_missing: Optional[Callable] = None) -> None:
        self.on_missing = self.on_missing_default
        if callable(on_missing):
            self.on_missing = on_missing

        # Allows to easily change and e.g. use ExtendedCfgPath with deep
        # search support
        self.cfg_path_type = CfgPath

    def new_context(
        self,
        data: ContainerType,
        *,
        on_missing: Optional[OnMissing] = None,
        current_file: Optional[ContainerType] = None,
        global_file: Optional[ContainerType] = None,
        **kvargs,
    ) -> GetterContext:
        """Assign a new context to the getter, optionally providing
        `on_missing` and `getter` overrides
        """

        if not callable(on_missing):
            on_missing = self.on_missing

        return GetterContext(
            data,
            current_file=current_file,
            global_file=global_file,
            on_missing=on_missing,
            args=kvargs,
        )

    def cb_get(self, data, key, ctx: GetterContext) -> Any:
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
        if isinstance(exc, ConfigException):
            raise exc

        trace = new_trace(ctx)
        raise ConfigException(f"Config not found: {ctx.cur_path()}", trace=trace)

    def get_path(self, ctx: GetterContext, path: PathType) -> list[str | int]:
        """Determine the real path.

        The base implementation just returns the normalized path, without
        validating, that the elements exist.

        Subclasses may extend the behavior and provide searching, e.g. `a..c`,
        `a.*.c`, `a.b[*].c`, etc.. Returning the path to the element found.

        :param path: A user provided (config) path like object, e.g. `a.b[2].c`
        :return: the normalized path
        """

        try:
            for ctx in self.walk_path(ctx, path):
                ctx.data = self.cb_get(ctx.data, ctx.key, ctx)
        except (KeyError, IndexError) as exc:
            trace = new_trace(ctx=ctx)
            raise ConfigException(
                f"Config not found: '{ctx.cur_path()}'", trace=trace
            ) from exc

        return ctx.path

    def get(self, ctx: GetterContext, path: PathType, default: Any = DEFAULT) -> Any:
        """Walk the provided path and return whatever the value at that
        end of that path is.

        :param path: A user provided (config) path like object, e.g. `a.b[2].c`
        :param default: Optional default value, if the value was not found
        """

        path = self.cfg_path_type(path)
        logger.debug("Config get(path=%s)", path)
        assert isinstance(ctx, GetterContext)

        recursions = []

        # pylint: disable=redefined-argument-from-local
        for ctx in self.walk_path(ctx, path):
            if isinstance(ctx.current_file, ConfigFile):
                logger.debug(
                    "Current context is: %s", relative_to_cwd(ctx.current_file.file_1)
                )

            try:
                ctx.data = self.cb_get(ctx.data, ctx.key, ctx)
            except (KeyError, IndexError, TypeError, ConfigException) as exc:
                logger.debug("Failure: %s", repr(exc))

                if default is not DEFAULT:
                    return default

                if callable(ctx.on_missing):
                    ctx.data = ctx.on_missing(ctx, exc)
                else:
                    ctx.data = self.on_missing(ctx, exc)

                if not isinstance(ctx.data, ContainerType):
                    return ctx.data

            if ctx.data in recursions:
                raise ConfigException(
                    f"Recursion detected: '{ctx.cur_path()}'", trace=new_trace(ctx=ctx)
                )

            recursions.append(ctx.data)

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

        ctx.path = self.cfg_path_type(path)
        if not ctx.path:
            return

        try:
            ctx.idx = 0
            while ctx.idx < len(ctx.path):
                ctx.key = ctx.path[ctx.idx]
                yield ctx
                ctx.idx += 1
        except (KeyError, IndexError) as exc:
            trace = new_trace(ctx=ctx)
            raise ConfigException(
                f"Config not found: '{ctx.cur_path()}'", trace=trace
            ) from exc

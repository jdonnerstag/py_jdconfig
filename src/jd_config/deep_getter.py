#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
An expandable base class to retrieve (get) elements in deep container structures,
e.g. Mapping and NonStrSequence.

Either the base class or a subclass should support:
- Support for any container type, that can hold 0-N values (e.g. Mapping, Sequence)
- Options to handle missing elements when walking the path. Default is to raise an
  exception. But it should also be possible to automatically add the missing elements.
  Whatever type they may require.
- Optionally, but not strictly required, register the new object with the parent.
- Support path search patterns, e.g. "a.*.c", "a.**.c", "a.b[*].c"
- Support ways to evaluate the values retrieved, e.g. `{ref:a}`, and return what
  it evaluates to (replacing the original value).
- In deep update scenarios it must be possible to replace existing nodes. E.g.
  replace an existing int or string value, with a dict or list.
"""

import logging
from typing import Any, Callable, Iterator, Optional

from .config_path import CfgPath, PathType
from .file_loader import ConfigFile
from .getter_context import GetterContext
from .utils import DEFAULT, ConfigException, ContainerType, relative_to_cwd

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


OnMissing = Callable[["GetterContext", Exception], Any]


GetterFn = Callable[[Any, str | int, "GetterContext", Callable[[], "GetterFn"]], Any]


class DeepGetter:
    """Getter for deep container structures (Mapping and NonStrSequence).

    This is one of the core classes of the config package. It works in close
    collaboration with GetterContext to provide the extensability and
    flexibility we need.
    """

    def __init__(
        self,
        *,
        ctx: Optional[GetterContext] = None,
        on_missing: Optional[Callable] = None,
    ) -> None:
        if ctx is not None:
            self.getter_pipeline = ctx.getter_pipeline
        else:
            self.getter_pipeline: tuple[GetterFn] = (self.cb_get,)

        self.on_missing = self.on_missing_default
        if callable(on_missing):
            self.on_missing = on_missing

        # Can be changed to e.g. ExtendedCfgPath, for deep search support
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
        """Create a new context with the data provided"""

        if not callable(on_missing):
            on_missing = self.on_missing

        return GetterContext(
            data,
            current_file=current_file,
            global_file=global_file,
            on_missing=on_missing,
            getter_pipeline=self.getter_pipeline,
            args=kvargs,
        )

    def exec_pipeline(self, data, key, ctx):
        ctx.getter_pipeline = self.getter_pipeline
        idx = [0]

        def next_fn() -> GetterFn:
            idx[0] += 1
            fn = self.getter_pipeline[idx[0]]
            return fn

        data = self.getter_pipeline[0](data, key, ctx, next_fn)
        return data

    @staticmethod
    def cb_get(data, key: str | int, ctx: GetterContext, next_fn: GetterFn) -> Any:
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

        raise ctx.exception(f"Config not found: {ctx.cur_path()}")

    def get_path(self, ctx: GetterContext, path: PathType) -> list[str | int]:
        """Determine the path if it exists, or throw an exception

        The implementation walks the path, to make sure the elements exist,
        can be resolved, or added if missing.

        Subclasses may extend the behavior and provide searching, e.g. `a.**.c`,
        `a.*.c`, `a.b[*].c`, etc.. Returning the path to the element found.

        :param path: A user provided path like object, e.g. `a.b[2].c`
        :return: the normalized path
        """

        ctx = self._get(ctx, path)
        return ctx.path

    def get(self, ctx: GetterContext, path: PathType, default: Any = DEFAULT) -> Any:
        """Walk the provided path and return whatever the value is. Might be a
        leaf node, or a container.

        :param path: A user provided (config) path like object, e.g. `a.b[2].c`
        :param default: Optional default value, if the value was not found
        """

        ctx = self._get(ctx, path, default)
        return ctx.data

    def _get(
        self, ctx: GetterContext, path: PathType, default: Any = DEFAULT
    ) -> GetterContext:
        """Walk the provided path, resolve placeholders if needed, add
        missing elements if needed, and return the context upon reaching
        the end of the path. Or throw an exception.

        :param path: A user provided (config) path like object, e.g. `a.b[2].c`
        :param default: Optional default value, if the value was not found
        :return: The context upon reaching the end of the path
        """

        path = self.cfg_path_type(path)
        logger.debug("Config get(path=%s)", path)
        assert isinstance(ctx, GetterContext)

        recursions = []

        for _ in self.walk_path(ctx, path):
            if isinstance(ctx.current_file, ConfigFile):
                logger.debug(
                    "Context has changed to: %s",
                    relative_to_cwd(ctx.current_file.file_1),
                )

            try:
                # ctx.data = self.cb_get(ctx.data, ctx.key, ctx)
                ctx.data = self.exec_pipeline(ctx.data, ctx.key, ctx)
            except (KeyError, IndexError, TypeError, ConfigException) as exc:
                logger.debug("Failure: %s", repr(exc))

                if default is not DEFAULT:
                    ctx.data = default
                    return ctx

                if callable(ctx.on_missing):
                    ctx.data = ctx.on_missing(ctx, exc)
                elif callable(self.on_missing):
                    ctx.data = self.on_missing(ctx, exc)
                else:
                    raise ctx.exception(f"Config not found: {ctx.cur_path()}") from exc

                if not isinstance(ctx.data, ContainerType):
                    return ctx

            if ctx.data in recursions:
                raise ctx.exception(f"Recursion detected: '{ctx.cur_path()}'")

            recursions.append(ctx.data)

        return ctx

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
            raise ctx.exception(f"Config not found: '{ctx.cur_path()}'") from exc

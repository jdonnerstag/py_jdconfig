#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Getter for deep container structures (Mapping and NonStrSequence)
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Mapping

from .utils import NonStrSequence, PathType, ConfigException, DEFAULT
from .config_path import ConfigPath

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


@dataclass
class GetterContext:
    data: Mapping | NonStrSequence
    key: str | int
    path: tuple[str | int]
    idx: int
    memo: list = field(default_factory=list)

    def cur_path(self) -> tuple[str | int]:
        return self.path[: self.idx] + (self.key,)


class DeepGetter:
    """Getter for deep container structures (Mapping and NonStrSequence)"""

    def __init__(
        self, data: Mapping | NonStrSequence, path: PathType, *, _memo=()
    ) -> None:
        self._data = data
        self._path = path
        self._memo = _memo

    def cb_get(self, data, key, _path) -> Any:
        """Retrieve the element. Subclasses may expand it, e.g. to resolve
        placeholders
        """
        return data[key]

    def cb_get_2_with_context(self, ctx: GetterContext) -> Any:
        """Internal:"""
        return self.cb_get(ctx.data, ctx.key, ctx.cur_path())

    def cb_get_3_with_missing(self, ctx: GetterContext) -> Any:
        """Internal:"""
        try:
            return self.cb_get_2_with_context(ctx)
        except (KeyError, IndexError) as exc:
            rtn = self.on_missing(ctx, exc)
            return rtn

    def on_missing(self, ctx: GetterContext, exc) -> Any:
        """A callback invoked, if a path can not be found.

        Subclasses may auto-create elements if needed.
        By default, the exception is re-raised.
        """
        return self.on_missing_default(ctx, exc)

    def on_missing_default(self, ctx: GetterContext, exc) -> Any:
        """A callback invoked, if a path can not be found.

        Subclasses may auto-create elements if needed.
        By default, the exception is re-raised.
        """
        path = ctx.cur_path()
        raise ConfigException(f"Config not found: '{path}'") from exc

    def normalize_path(self, path: PathType) -> tuple[str | int]:
        """Normalize a path"""

        # TODO Need a version without search pattern support
        return tuple(ConfigPath.normalize_path(path))

    def new_context(self, data, path, _memo) -> GetterContext:
        """Create a new context. Allow subclasses to provide an extended version"""
        return GetterContext(data, path[0], path, 0, _memo)

    def get(self, path: PathType, default: Any = DEFAULT, *, _memo=None) -> Any:
        """Get ..."""

        path = self.normalize_path(path)
        if not path:
            return self._data

        ctx = self.new_context(self._data, path, _memo)
        try:
            ctx = self._get_ctx(ctx)
            return ctx.data
        except (KeyError, IndexError, ConfigException) as exc:
            if default is not DEFAULT:
                return default

            if isinstance(exc, ConfigException):
                raise

            raise ConfigException(f"Config not found: '{ctx.cur_path()}'") from exc

    def _get_ctx(self, ctx: GetterContext) -> GetterContext:
        while ctx.idx < len(ctx.path):
            ctx.key = ctx.path[ctx.idx]
            ctx.data = self.cb_get_3_with_missing(ctx)
            ctx.idx += 1

        return ctx

    def get_path(self, path: PathType) -> list[str | int]:
        """Determine the real path by replacing the search patterns"""

        return self.normalize_path(path)

#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Extended standard dict like getter to also support deep paths, and also
search patterns, such as 'a..c', 'a.*.c'
"""

import logging
from typing import Any, Mapping

from .utils import NonStrSequence, PathType, ConfigException
from .config_path import ConfigPath
from .deep_getter_base import DeepGetter, GetterContext
from .objwalk import ObjectWalker

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


class DeepGetterWithSearch(DeepGetter):
    """Extended standard dict like getter to also support deep paths, and also
    search patterns, such as 'a..c', 'a.*.c'
    """

    def cb_get_2_with_context(self, ctx: GetterContext) -> Any:
        if ctx.key == ConfigPath.PAT_ANY_KEY:
            return self.on_any_key(ctx)
        if ctx.key == ConfigPath.PAT_ANY_IDX:
            return self.on_any_idx(ctx)
        if ctx.key == ConfigPath.PAT_DEEP:
            return self.on_any_deep(ctx)

        return super().cb_get_2_with_context(ctx)

    def get_path(self, path: PathType) -> list[str | int]:
        """Determine the real path by replacing the search patterns"""

        path = super().get_path(path)
        if not path:
            return path

        ctx = self.new_context(self._data, path, [])
        ctx = self._get_ctx(ctx)
        return ctx.path

    def on_any_key(self, ctx: GetterContext) -> Any:
        """Callback if 'a.*.c' was found"""

        if not isinstance(ctx.data, Mapping):
            raise ConfigException(f"Expected a Mapping: '{ctx.cur_path()}'")

        find_key = ctx.path[ctx.idx + 1]
        for key in ctx.data.keys():
            # Allow to resolve placeholder if necessary
            ctx.key = key
            value = self.cb_get_2_with_context(ctx)

            if isinstance(value, Mapping) and isinstance(find_key, str):
                if find_key in value:
                    ctx.data = value[find_key]
                    ctx.path = self._path_replace(ctx.path, ctx.idx, key)
                    ctx.idx += 1
                    return ctx.data
            elif isinstance(value, NonStrSequence) and isinstance(find_key, int):
                if 0 <= find_key < len(value):
                    ctx.data = value[find_key]
                    ctx.path = self._path_replace(ctx.path, ctx.idx, key)
                    ctx.idx += 1
                    return ctx.data

        raise ConfigException(f"Config not found: '{ctx.cur_path()}'")

    def on_any_idx(self, ctx: GetterContext) -> GetterContext:
        """Callback if 'a[*].b' was found"""

        if not isinstance(ctx.data, NonStrSequence):
            raise ConfigException(f"Expected a Sequence: '{ctx.cur_path()}'")

        find_key = ctx.path[ctx.idx + 1]
        for key, value in enumerate(ctx.data):
            # Allow to resolve placeholder if necessary
            ctx.key = key
            value = self.cb_get_2_with_context(ctx)

            if isinstance(value, Mapping) and isinstance(find_key, str):
                if find_key in value:
                    ctx.data = value[find_key]
                    ctx.path = self._path_replace(ctx.path, ctx.idx, key)
                    ctx.idx += 1
                    return ctx.data
            elif isinstance(value, NonStrSequence) and isinstance(find_key, int):
                if 0 <= find_key < len(value):
                    ctx.data = value[find_key]
                    ctx.path = self._path_replace(ctx.path, ctx.idx, key)
                    ctx.idx += 1
                    return ctx.data

        raise ConfigException(f"Config not found: '{ctx.cur_path()}'")

    def on_any_deep(self, ctx: GetterContext) -> GetterContext:
        """Callback if 'a..b' was found"""

        find_key = ctx.path[ctx.idx + 1]
        walk = ObjectWalker.objwalk
        for event in walk(ctx.data, nodes_only=False, cb_get=self.cb_get):
            if event.path and event.path[-1] == find_key:
                ctx.data = event.value
                ctx.path = self._path_replace(ctx.path, ctx.idx, event.path, 2)
                ctx.idx += len(event.path) - 1
                return ctx.data

        raise ConfigException(f"Config not found: '{ctx.cur_path()}'")

    def _path_replace(self, path, idx, replace, count = 1) -> tuple:
        if not isinstance(replace, tuple):
            replace = (replace,)

        return path[: idx] + replace + path[idx + count:]

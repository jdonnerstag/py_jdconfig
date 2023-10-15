#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Extended standard dict like getter to also support deep paths, and also
search patterns, such as 'a..c', 'a.*.c'
"""

import logging
from typing import Any, Iterator, Mapping

from .utils import NonStrSequence, ConfigException
from .config_path import ConfigPath
from .deep_getter_base import GetterContext
from .objwalk import ObjectWalker, WalkerEvent

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


class ConfigSearchMixin:
    """Extended standard dict like getter to also support deep paths, and also
    search patterns, such as 'a..c', 'a.*.c'
    """

    def cb_get_2_with_context(self, ctx: GetterContext) -> Any:
        if ctx.key == ConfigPath.PAT_ANY_KEY:
            return self._on_any_key(ctx)
        if ctx.key == ConfigPath.PAT_ANY_IDX:
            return self._on_any_idx(ctx)
        if ctx.key == ConfigPath.PAT_DEEP:
            return self._on_any_deep(ctx)

        return super().cb_get_2_with_context(ctx)

    def _on_any_key(self, ctx: GetterContext) -> Any:
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
                    ctx.path = ctx.path_replace(key)
                    ctx.idx += 1
                    return ctx.data
            elif isinstance(value, NonStrSequence) and isinstance(find_key, int):
                if 0 <= find_key < len(value):
                    ctx.data = value[find_key]
                    ctx.path = ctx.path_replace(key)
                    ctx.idx += 1
                    return ctx.data

        raise ConfigException(f"Config not found: '{ctx.cur_path()}'")

    def _on_any_idx(self, ctx: GetterContext) -> GetterContext:
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
                    ctx.path = ctx.path_replace(key)
                    ctx.idx += 1
                    return ctx.data
            elif isinstance(value, NonStrSequence) and isinstance(find_key, int):
                if 0 <= find_key < len(value):
                    ctx.data = value[find_key]
                    ctx.path = ctx.path_replace(key)
                    ctx.idx += 1
                    return ctx.data

        raise ConfigException(f"Config not found: '{ctx.cur_path()}'")

    def _on_any_deep(self, ctx: GetterContext) -> GetterContext:
        """Callback if 'a..b' was found"""

        find_key = ctx.path[ctx.idx + 1]
        for event in self.walk_tree(ctx.data, nodes_only=False):
            if event.path and event.path[-1] == find_key:
                ctx.data = event.value
                ctx.path = ctx.path_replace(event.path, 2)
                ctx.idx += len(event.path) - 1
                return ctx.data

        raise ConfigException(f"Config not found: '{ctx.cur_path()}'")

    def walk_tree(
        self, obj: Mapping | NonStrSequence, *, nodes_only: bool = False
    ) -> Iterator[WalkerEvent]:
        """Like walking a deep filesystem, walk a deep object structure"""

        walk = ObjectWalker.objwalk
        yield from walk(obj, nodes_only=nodes_only, cb_get=self.cb_get)

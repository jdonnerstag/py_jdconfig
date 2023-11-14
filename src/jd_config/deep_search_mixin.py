#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Extended standard dict like getter to also support deep paths, and also
search patterns, such as 'a..c', 'a.*.c'
"""

import logging
from dataclasses import replace
from typing import Any, Iterator, Mapping

from .config_path import CfgPath
from .config_path_extended import ExtendedCfgPath
from .deep_getter import GetterContext
from .objwalk import WalkerEvent, objwalk
from .placeholders import new_trace
from .utils import ConfigException, ContainerType, NonStrSequence

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


class DeepSearchMixin:
    """Extended standard dict like getter to also support deep paths, and also
    search patterns, such as 'a..c', 'a.*.c'
    """

    def cb_get(self, data, key, ctx: GetterContext) -> Any:
        """Retrieve an element from its parent container.

        See DeepGetter.cb_get() for more details.
        """
        if key == ExtendedCfgPath.PAT_ANY_KEY:
            return self._on_any_key(ctx)
        if key == ExtendedCfgPath.PAT_ANY_IDX:
            return self._on_any_idx(ctx)
        if key == ExtendedCfgPath.PAT_DEEP:
            return self._on_any_deep(ctx)

        return super().cb_get(data, key, ctx)

    def _on_any_key(self, ctx: GetterContext) -> Any:
        """Callback if 'a.*.c' was found"""

        if not isinstance(ctx.data, Mapping):
            raise ConfigException(
                f"Expected a Mapping: '{ctx.cur_path()}'", trace=new_trace(ctx=ctx)
            )

        find_key = ctx.path[ctx.idx + 1]
        for key in ctx.data.keys():
            if self._for_each_key(ctx, key, find_key):
                return ctx.data

        raise ConfigException(
            f"Config not found: '{ctx.cur_path()}'", trace=new_trace(ctx=ctx)
        )

    def _on_any_idx(self, ctx: GetterContext) -> GetterContext:
        """Callback if 'a[*].b' was found"""

        if not isinstance(ctx.data, NonStrSequence):
            raise ConfigException(
                f"Expected a Sequence: '{ctx.cur_path()}'", trace=new_trace(ctx=ctx)
            )

        find_key = ctx.path[ctx.idx + 1]
        for key, _ in enumerate(ctx.data):
            if self._for_each_key(ctx, key, find_key):
                return ctx.data

        raise ConfigException(
            f"Config not found: '{ctx.cur_path()}'", trace=new_trace(ctx=ctx)
        )

    def _for_each_key(self, ctx: GetterContext, key: str | int, find_key) -> bool:
        # Allow to resolve placeholder if necessary
        ctx.key = key
        value = self.cb_get(ctx.data, ctx.key, ctx)

        # Test "*.*.b" use cases
        if find_key == ExtendedCfgPath.PAT_ANY_KEY and isinstance(value, ContainerType):
            ctx.data = value
            ctx.path = ctx.path_replace(key)
            ctx.idx += 1
            return self._on_any_key(ctx)

        if isinstance(value, Mapping) and isinstance(find_key, str):
            if find_key in value:
                ctx.data = value[find_key]
                ctx.path = ctx.path_replace(key)
                ctx.idx += 1
                return True
        elif isinstance(value, NonStrSequence) and isinstance(find_key, int):
            if 0 <= find_key < len(value):
                ctx.data = value[find_key]
                ctx.path = ctx.path_replace(key)
                ctx.idx += 1
                return True

        return False

    def _on_any_deep(self, ctx: GetterContext) -> GetterContext:
        """Callback if 'a..b' was found"""

        find_key = ctx.path[ctx.idx + 1]
        for event in self.walk_tree(ctx, nodes_only=False):
            if event.path and event.path[-1] == find_key:
                ctx.data = event.value
                ctx.path = ctx.path_replace(event.path, 2)
                ctx.idx += len(event.path) - 1
                return ctx.data

        raise ConfigException(
            f"Config not found: '{ctx.cur_path()}'", trace=new_trace(ctx=ctx)
        )

    def walk_tree(
        self, ctx: GetterContext, *, nodes_only: bool = False
    ) -> Iterator[WalkerEvent]:
        """Like walking a deep filesystem, walk a deep object structure"""

        ctx_stack = [ctx]

        def cb_get(data, key, _path):
            logger.debug("objwalk: path=%s", _path + (key,))

            while (len(ctx_stack) - 1) > len(_path):
                ctx_stack.pop()

            if len(_path) >= (len(ctx_stack) - 1):
                cur_ctx = ctx_stack[-1]
                new_ctx = replace(cur_ctx, data=data)
                ctx_stack.append(new_ctx)

            cur_ctx = ctx_stack[-1]
            cur_ctx.memo = None
            cur_ctx.key = key

            return self.cb_get(data, key, ctx=cur_ctx)

        yield from objwalk(ctx.data, nodes_only=nodes_only, cb_get=cb_get)
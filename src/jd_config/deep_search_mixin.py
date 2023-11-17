#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Extended standard dict like getter to also support deep paths, and also
search patterns, such as 'a..c', 'a.*.c'
"""

import logging
from typing import Any

from jd_config.config_path import CfgPath

from .config_path_extended import ExtendedCfgPath
from .utils import DEFAULT, ContainerType

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


class DeepSearchMixin:
    """Extended standard dict like getter to also support deep paths, and also
    search patterns, such as 'a.**.c', 'a.*.c'
    """

    path_type = ExtendedCfgPath

    # @override
    def _get(self, path: CfgPath, **kvargs) -> (Any, CfgPath):
        """Retrieve an element from its parent container.

        See DeepGetter.cb_get() for more details.
        """
        key = path[0]
        cur_path = self.path(key)
        if key == ExtendedCfgPath.PAT_ANY_KEY:
            if not self.is_mapping():
                raise KeyError(
                    f"Expected a Mapping: '{cur_path}'"  # , trace=new_trace(ctx=ctx)
                )
            return self._on_any_key_or_idx(path, **kvargs)

        if key == ExtendedCfgPath.PAT_ANY_IDX:
            if not self.is_sequence():
                raise KeyError(
                    f"Expected a Sequence: '{cur_path}'"  # , trace=new_trace(ctx=ctx)
                )
            return self._on_any_key_or_idx(path, **kvargs)

        if key == ExtendedCfgPath.PAT_DEEP:
            if not self.is_mapping() and not self.is_sequence():
                raise KeyError(
                    f"Expected a Mapping or Sequence: '{cur_path}'"  # , trace=new_trace(ctx=ctx)
                )
            return self._on_any_deep(path, **kvargs)

        return super()._get(path, **kvargs)

    def _on_any_key_or_idx(self, path: CfgPath, **kvargs) -> (Any, CfgPath):
        """Callback if 'a.*.c' was found"""

        for key, data in self.items():
            if not isinstance(data, ContainerType):
                continue

            child = self.clone(data, key)
            try:
                value, rest_path = child._get(path[1:], **kvargs)
                return value, rest_path
            except KeyError:
                pass  # ignore

        cur_path = self.path_type(self.path(path[0:2]))
        raise KeyError(f"Config not found: '{cur_path}'")  # , trace=new_trace(ctx=ctx)

    def _on_any_deep(self, path: CfgPath, **kvargs) -> (Any, CfgPath):
        """Callback if 'a..b' was found"""

        find_key = path[1]
        for key, data in self.items():
            if key == find_key:
                return data, path[2:]

            if not isinstance(data, ContainerType):
                continue

            child = self.clone(data, key)
            try:
                value = child.get(path, **kvargs)
                return value, path[2:]
            except (KeyError, IndexError, TypeError):
                pass  # ignore

        cur_path = self.path_type(self.path(path[0:2]))
        raise KeyError(f"Config not found: '{cur_path}'")  # , trace=new_trace(ctx=ctx)

#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Mixin to export deep config data
"""

import logging
from functools import partial
from typing import Any, Mapping, Optional, Sequence

import yaml

from .objwalk import (
    DropContainerEvent,
    NewMappingEvent,
    NewSequenceEvent,
    NodeEvent,
    ObjectWalker,
)
from .utils import ContainerType, PathType

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


class DeepExportMixin:
    """A mixin to export configs into dict or yaml structures.

    Dependencies:
    - self.data: the config object structure
    - self.resolve(): a method to lazily resolve placeholders
    - self.get(): acces a (deep) config node
    """

    def __init__(self) -> None:
        assert hasattr(self, "get"), "Mixin depends on self.get()"
        assert hasattr(self, "cb_get"), "Mixin depends on self.cb_get()"

    def to_dict(
        self, data: ContainerType, path: Optional[PathType] = None, resolve: bool = True
    ) -> dict:
        """Walk the config items with an optional starting point, and create a
        dict from it.
        """

        ctx = self.new_context(data)
        cb_get = partial(self.cb_get, ctx=ctx, skip_resolver=not resolve, clear_memo=True)
        root = self.get(data, path)
        cur: Mapping | Sequence = {}
        stack = [cur]

        for event in ObjectWalker.objwalk(root, nodes_only=False, cb_get=cb_get):
            if isinstance(event, (NewMappingEvent, NewSequenceEvent)):
                new = event.new()
                stack.append(new)
                if event.path:
                    self._add_to_dict_or_list(cur, event.path[-1], new)
                cur = new
            elif isinstance(event, DropContainerEvent):
                stack.pop()
                if stack:
                    cur = stack[-1]
            elif isinstance(event, NodeEvent):
                value = event.value
                self._add_to_dict_or_list(cur, event.path[-1], value)

        return cur

    @classmethod
    def _add_to_dict_or_list(cls, obj: Mapping | Sequence, key: str, value: Any):
        if isinstance(obj, Mapping):
            obj[key] = value
        elif isinstance(obj, Sequence):
            obj.append(value)

    def to_yaml(self, data: ContainerType, path: Optional[PathType] = None, stream=None, **kvargs):
        """Convert the configs (or part of it), into a yaml document"""

        data = self.to_dict(data, path, resolve=True)
        return yaml.dump(data, stream, **kvargs)

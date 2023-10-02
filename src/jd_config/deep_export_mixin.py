#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Mixin to export deep config data
"""

import logging
from typing import Any, Mapping, Optional, Sequence

import yaml

from .config_getter import PathType

from .objwalk import (
    DropContainerEvent,
    NewMappingEvent,
    NewSequenceEvent,
    NodeEvent,
    ObjectWalker,
)

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
        assert hasattr(self, "data"), "Mixin depends on self.data"
        assert hasattr(self, "resolve"), "Mixin depends on self.resolve()"
        assert hasattr(self, "get"), "Mixin depends on self.get()"

    def to_dict(self, root: Optional[PathType] = None, resolve: bool = True) -> dict:
        """Walk the config items with an optional starting point, and create a
        dict from it.
        """

        obj = self.data
        if root:
            obj = self.get(root)

        cur: Mapping | Sequence = {}
        stack = [cur]

        for event in ObjectWalker.objwalk(obj, nodes_only=False):
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
                if resolve:
                    if hasattr(value, "value"):
                        value = value.value
                    value = self.resolve(value, self.data)

                self._add_to_dict_or_list(cur, event.path[-1], value)

        return cur

    @classmethod
    def _add_to_dict_or_list(cls, obj: Mapping | Sequence, key: str, value: Any):
        if isinstance(obj, Mapping):
            obj[key] = value
        elif isinstance(obj, Sequence):
            obj.append(value)

    def to_yaml(self, root: Optional[PathType] = None, stream=None, **kvargs):
        """Convert the configs (or part of it), into a yaml document"""

        data = self.to_dict(root, resolve=True)
        return yaml.dump(data, stream, **kvargs)

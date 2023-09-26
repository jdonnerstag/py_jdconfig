#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Mixin to export deep config data
"""

import logging
from typing import Mapping, Optional
import yaml
from .objwalk import objwalk, NodeEvent, NewMappingEvent, NewSequenceEvent, DropContainerEvent
from .config_getter import PathType


__parent__name__ = __name__.rpartition('.')[0]
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


    def to_dict(self, root: Optional[PathType] = None, resolve: bool = True) -> dict:
        """Walk the config items with an optional starting point, and create a
        dict from it.
        """

        obj = self.data
        if root:
            obj = self.get(root)

        stack = []
        for event in objwalk(obj, nodes_only=False):
            if isinstance(event, (NewMappingEvent, NewSequenceEvent)):
                if isinstance(event, NewMappingEvent):
                    new = {}
                else:
                    new = []
                stack.append(new)
                if event.path:
                    if isinstance(cur, Mapping):
                        cur[event.path[-1]] = new
                    else:
                        cur.append(new)
                cur = new
            elif isinstance(event, DropContainerEvent):
                stack.pop()
                if stack:
                    cur = stack[-1]
            elif isinstance(event, NodeEvent):
                value = event.value
                if resolve:
                    value = self.resolve(event.value.value, self.data)

                if isinstance(cur, Mapping):
                    cur[event.path[-1]] = value
                else:
                    cur.append(value)

        return cur

    def to_yaml(self, root: Optional[PathType] = None, stream = None, **kvargs):
        """Convert the configs (or part of it), into a yaml document
        """

        data = self.to_dict(root, resolve=True)
        return yaml.dump(data, stream, **kvargs)

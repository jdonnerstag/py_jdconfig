#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Walk a tree-like structure of Mapping- and Sequence-like objects, and yield
events when stepping into or out of a container, and for every leaf-node.

This is similar to walking a file system or directory structure.
"""

import logging
from dataclasses import dataclass
from typing import Any, Callable, Iterator, Mapping, Optional

from .config_path import CfgPath, PathType
from .utils import ConfigException, ContainerType, NonStrSequence

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


@dataclass(eq=False)
class WalkerEvent:
    """The common base class for all objwalk events"""

    # The path to the config value
    path: CfgPath

    # The config value itself
    value: Any

    # The parent container (map, list), containing the node
    container: ContainerType

    # Available to users. If true, all remaining nodes of the current
    # parent container are skipped.
    skip: bool = False

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, WalkerEvent):
            return False

        return (self.path == value.path) and (self.value == value.value)


@dataclass(eq=False)
class NodeEvent(WalkerEvent):
    """An objwalk node event"""


@dataclass(eq=False)
class NewMappingEvent(WalkerEvent):
    """Entering a new mapping"""

    @classmethod
    def new(cls):
        """Create a new dict"""
        return {}


@dataclass(eq=False)
class NewSequenceEvent(WalkerEvent):
    """Entering a new Sequence"""

    @classmethod
    def new(cls):
        """Create a new list"""
        return []


@dataclass(eq=False)
class DropContainerEvent(WalkerEvent):
    """Step out of a Mapping or Sequence"""


def objwalk(
    obj: Mapping | NonStrSequence,
    *,
    nodes_only: bool = False,
    cb_get: Optional[Callable[[ContainerType, str | int, PathType], Any]] = None,
) -> Iterator[WalkerEvent]:
    """A generic function to walk any Mapping- and Sequence- like objects.

    Once loaded into memory, Yaml and Json files, are often implemented with
    nested dict- and list-like object structures.

    'objwalk' walks the structure depth first.

    It has one important feature (required for configs): Imagine an entry such as 'a: "{ref:b}"',
    and 'b: {c: 99}'. "{ref:b}" is a reference to "b", and "b" is a map. Hence "a" is not a
    leaf-node and neither a string value. The 'cb_get' argument is an optional function to 'get'
    the item from a container and possibly post-process it: parse and interprete "{ref:b}" and
    replace the return value with "b".

    :param obj: The root container to start walking.
    :param nodes_only: If True, only the leaf node events are yielded
    :param cb_get: An optional function to 'get' the item from a container.
    :return: 'objwalk' is a generator function, yielding events with information about path and obj.
    """

    if not obj:
        return

    if not isinstance(obj, (Mapping, NonStrSequence)):
        yield NodeEvent(path=(), value=obj, container=None)
        return

    creator_map = {Mapping: NewMappingEvent, NonStrSequence: NewSequenceEvent}

    path_ = CfgPath()  # Empty
    iter_obj = [obj]
    iter_stack = [_container_iter(obj)]

    while iter_stack:
        cur = iter_stack[-1]
        try:
            key = next(cur)
            value = iter_obj[-1]
            value = value[key] if cb_get is None else cb_get(value, key, path_)

            event = None
            for type_, event_type in creator_map.items():
                if not isinstance(value, type_):
                    continue

                path_ = path_ + key
                if not nodes_only:
                    event = event_type(path_, value, iter_obj[-1])
                    yield event
                iter_obj.append(value)
                iter_stack.append(_container_iter(value))
                break
            else:
                event = NodeEvent(path_ + (key,), value, iter_obj[-1])
                yield event

            if event and event.skip:
                raise StopIteration

        except StopIteration:
            value = iter_obj.pop()
            if not nodes_only and iter_obj:
                yield DropContainerEvent(path_, value, iter_obj[-1])

            iter_stack.pop()
            path_ = CfgPath(path_[:-1])


def _container_iter(obj: Mapping | NonStrSequence) -> Iterator:
    if isinstance(obj, Mapping):
        return iter(obj.keys())

    if isinstance(obj, NonStrSequence):
        return iter(range(len(obj)))

    raise ConfigException(f"Bug? Expected either Mapping or NonStrSequence: {obj}")

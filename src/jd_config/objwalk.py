#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Walk a tree-like structure of Mapping- and Sequence-like object, and yield
events when stepping into or out of a container, and for every leaf-node.
"""

import logging
from dataclasses import dataclass
from typing import Any, Callable, Iterator, Mapping, Optional, Tuple

from .utils import ConfigException, ContainerType, NonStrSequence

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


@dataclass(eq=False)
class WalkerEvent:
    """An objwalk node event"""

    path: Tuple[str | int, ...]
    value: Any
    container: ContainerType
    skip: bool = False

    def is_sequence_node(self) -> bool:
        """True, if node belongs to a Sequence"""
        return isinstance(self.path[-1], int)

    def is_mapping_node(self) -> bool:
        """True, if node belongs to a Mapping"""
        return not self.is_sequence_node()

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, WalkerEvent):
            return False

        return self.path == value.path and self.value == value.value


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
    """Step out of Mapping or Sequence"""


class ObjectWalker:
    """Walk a tree-like structure of Mapping- and Sequence-like object, and yield
    events when stepping into or out of a container, and for every leaf-node.
    """

    @classmethod
    def objwalk(
        cls,
        obj: Mapping | NonStrSequence,
        *,
        nodes_only: bool = False,
        cb_get: Optional[Callable] = None,
    ) -> Iterator[WalkerEvent]:
        """A generic function to walk any Mapping- and Sequence- like objects.

        Once loaded into memory, Yaml and Json files, are often implemented with
        nested dict- and list-like object structures.

        'objwalk' walks the structure depth first. Only leaf-nodes are yielded.

        :param obj: The root container to start walking.
        :return: 'objwalk' is a generator function, yielding the elements path and obj.
        """

        if not obj:
            return

        if not isinstance(obj, (Mapping, NonStrSequence)):
            yield NodeEvent(path=(), value=obj, container=None)
            return

        path_ = ()  # Empty tuple
        iter_obj = [obj]
        iter_stack = [cls._container_iter(obj)]

        while iter_stack:
            cur = iter_stack[-1]
            try:
                key = next(cur)
                value = iter_obj[-1]
                value = value[key] if cb_get is None else cb_get(value, key)

                event = None
                if isinstance(value, Mapping):
                    path_ = path_ + (key,)
                    if not nodes_only:
                        event = NewMappingEvent(path_, value, iter_obj[-1])
                        yield event
                    iter_obj.append(value)
                    iter_stack.append(cls._container_iter(value))
                elif isinstance(value, NonStrSequence):
                    path_ = path_ + (key,)
                    if not nodes_only:
                        event = NewSequenceEvent(path_, value, iter_obj[-1])
                        yield event
                    iter_obj.append(value)
                    iter_stack.append(cls._container_iter(value))
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
                path_ = path_[:-1]

    @classmethod
    def _container_iter(cls, obj: Mapping | NonStrSequence) -> Iterator:
        if isinstance(obj, Mapping):
            return iter(obj.keys())

        if isinstance(obj, NonStrSequence):
            return iter(range(len(obj)))

        raise ConfigException(f"Bug? Expected either Mapping or NonStrSequence: {obj}")

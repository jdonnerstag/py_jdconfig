#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Walk a tree-like structure of Mapping- and Sequence-like object, and yield
events when stepping into or out of a container, and for every leaf-node.
"""

import logging
from dataclasses import dataclass
from typing import Any, Iterator, Mapping, Optional, Sequence, Tuple

from .utils import ConfigException, NonStrSequence

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


@dataclass
class NodeEvent:
    """An objwalk node event"""

    path: Tuple[str | int, ...]
    value: Any
    container: Mapping | NonStrSequence
    skip: bool = False

    def is_sequence_node(self) -> bool:
        """True, if node belongs to a Sequence"""
        return isinstance(self.path[-1], int)

    def is_mapping_node(self) -> bool:
        """True, if node belongs to a Mapping"""
        return not self.is_sequence_node()


@dataclass
class NewMappingEvent:
    """Entering a new mapping"""

    path: Tuple[str | int, ...]
    value: Mapping
    skip: bool = False

    @classmethod
    def new(cls):
        """Create a new dict"""
        return {}


@dataclass
class NewSequenceEvent:
    """Entering a new Sequence"""

    path: Tuple[str | int, ...]
    value: Sequence
    skip: bool = False

    @classmethod
    def new(cls):
        """Create a new list"""
        return []


@dataclass
class DropContainerEvent:
    """Step out of Mapping or Sequence"""

    path: Tuple[str | int, ...]
    value: Mapping | NonStrSequence
    skip: bool = False


WalkerEvent = NodeEvent | NewMappingEvent | NewSequenceEvent | DropContainerEvent


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
        cb_get: Optional[callable] = None,
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
            yield NodeEvent((), obj, None)
            return

        path_ = ()  # Empty tuple
        iter_obj = [obj]
        iter_stack = [cls._container_iter(obj)]

        while iter_stack:
            cur = iter_stack[-1]
            try:
                key = next(cur)

                # get and resolve placeholders if needed.
                value = iter_obj[-1]
                value = cb_get(value, key, path_) if callable(cb_get) else value[key]

                event = None
                if isinstance(value, Mapping):
                    path_ = path_ + (key,)
                    if not nodes_only:
                        event = NewMappingEvent(path_, value)
                        yield event
                    iter_obj.append(value)
                    iter_stack.append(cls._container_iter(value))
                elif isinstance(value, NonStrSequence):
                    path_ = path_ + (key,)
                    if not nodes_only:
                        event = NewSequenceEvent(path_, value)
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
                    yield DropContainerEvent(path_, value)

                iter_stack.pop()
                path_ = path_[:-1]

    @classmethod
    def _container_iter(cls, obj: Mapping | NonStrSequence) -> Iterator:
        if isinstance(obj, Mapping):
            return iter(obj.keys())

        if isinstance(obj, NonStrSequence):
            return iter(range(len(obj)))

        raise ConfigException(f"Bug? Expected either Mapping or NonStrSequence: {obj}")

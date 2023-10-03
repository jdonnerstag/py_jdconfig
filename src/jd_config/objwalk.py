#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
A generic function to walk any Mapping- and Sequence- like objects.
"""

from abc import ABC
from dataclasses import dataclass
import logging
from typing import Any, Mapping, Sequence, Tuple, Iterator

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


@dataclass
class NodeEvent:
    """An objwalk node event"""

    path: Tuple[str | int, ...]
    value: Any
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

    path: [str | int, ...]
    value: Sequence
    skip: bool = False

    @classmethod
    def new(cls):
        """Create a new list"""
        return []


@dataclass
class DropContainerEvent:
    """Step out of Mapping or Sequence"""

    path: [str | int, ...]
    value: Mapping | Sequence
    skip: bool = False


WalkerEvent = NodeEvent | NewMappingEvent | NewSequenceEvent | DropContainerEvent


class NonStrSequence(ABC):
    """Avoid having to do `isinstance(x, Sequence) and not isinstance(x, str)` all the time"""

    @classmethod
    def __subclasshook__(cls, C: type):
        # not possible to do with AnyStr
        if C is str:
            return NotImplemented

        return issubclass(C, Sequence)


class ObjectWalker:
    """A generic function to walk any Mapping- and Sequence- like objects."""

    @classmethod
    def objwalk(
        cls, obj: Mapping | NonStrSequence, *, nodes_only: bool = False
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

        iter_stack = []
        iter_obj = []
        path_ = ()  # Empty tuple

        if isinstance(obj, Mapping):
            iter_obj.append(obj)
            iter_stack.append(iter(obj.items()))
        elif isinstance(obj, NonStrSequence):
            iter_obj.append(obj)
            iter_stack.append(iter(enumerate(obj)))
        else:
            yield NodeEvent(path_, obj)

        while iter_stack:
            cur = iter_stack[-1]
            try:
                key, value = next(cur)

                event = None
                if isinstance(value, Mapping):
                    path_ = path_ + (key,)
                    if not nodes_only:
                        event = NewMappingEvent(path_, value)
                        yield event
                    iter_obj.append(value)
                    iter_stack.append(iter(value.items()))
                elif isinstance(value, NonStrSequence):
                    path_ = path_ + (key,)
                    if not nodes_only:
                        event = NewSequenceEvent(path_, value)
                        yield event
                    iter_obj.append(value)
                    iter_stack.append(iter(enumerate(value)))
                else:
                    event = NodeEvent(path_ + (key,), value)
                    yield event

                if event and event.skip:
                    raise StopIteration

            except StopIteration:
                value = iter_obj.pop()
                if not nodes_only and iter_obj:
                    yield DropContainerEvent(path_, value)

                iter_stack.pop()
                path_ = path_[:-1]

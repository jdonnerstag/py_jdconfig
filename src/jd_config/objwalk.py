#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
A generic function to walk any Mapping- and Sequence- like objects.
"""

from dataclasses import dataclass
import logging
from typing import Any, Mapping, Optional, Sequence, Set, Tuple, Iterator

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


@dataclass
class NodeEvent:
    """An objwalk node event"""

    path: Tuple[str | int, ...]
    value: Any

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

    @classmethod
    def new(cls):
        """Create a new dict"""
        return {}


@dataclass
class NewSequenceEvent:
    """Entering a new Sequence"""

    path: [str | int, ...]

    @classmethod
    def new(cls):
        """Create a new list"""
        return []


@dataclass
class DropContainerEvent:
    """Step out of Mapping or Sequence"""


WalkerEvent = NodeEvent | NewMappingEvent | NewSequenceEvent | DropContainerEvent


class ObjectWalker:
    """A generic function to walk any Mapping- and Sequence- like objects."""

    @classmethod
    def objwalk(
        cls,
        obj: Any,
        *,
        _path: Tuple[str | int, ...] = (),
        _memo: Optional[Set] = None,
        nodes_only: bool = False
    ) -> Iterator[WalkerEvent]:
        """A generic function to walk any Mapping- and Sequence- like objects.

        Once loaded into memory, Yaml and Json files, are often implemented with
        nested dict- and list-like object structures.

        'objwalk' walks the structure depth first. Only leaf-nodes are yielded.

        :param obj: The root container to start walking.
        :param _path: internal use only.
        :param _memo: internal use only.
        :return: 'objwalk' is a generator function, yielding the elements path and obj.
        """

        # Detect recursion
        if _memo is None:
            _memo = set()

        if isinstance(obj, Mapping):
            yield from cls._on_mapping(obj, _path, _memo, nodes_only)
        elif isinstance(obj, (Sequence, Set)) and not isinstance(obj, str):
            yield from cls._on_sequence(obj, _path, _memo, nodes_only)
        else:
            yield NodeEvent(_path, obj)

    @classmethod
    def _on_mapping(cls, obj, path_, _memo, nodes_only) -> Iterator[WalkerEvent]:
        if id(obj) not in _memo:
            _memo.add(id(obj))
            if not nodes_only:
                yield NewMappingEvent(path_)
            for key, value in obj.items():
                for child in cls.objwalk(
                    value, _path=path_ + (key,), _memo=_memo, nodes_only=nodes_only
                ):
                    yield child
            if not nodes_only:
                yield DropContainerEvent()

    @classmethod
    def _on_sequence(cls, obj, path_, _memo, nodes_only) -> Iterator[WalkerEvent]:
        if id(obj) not in _memo:
            _memo.add(id(obj))
            if not nodes_only:
                yield NewSequenceEvent(path_)
            for index, value in enumerate(obj):
                for child in cls.objwalk(
                    value, _path=path_ + (index,), _memo=_memo, nodes_only=nodes_only
                ):
                    yield child
            if not nodes_only:
                yield DropContainerEvent()

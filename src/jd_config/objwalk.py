#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
A generic function to walk any Mapping- and Sequence- like objects.
"""

from dataclasses import dataclass
import logging
from typing import Any, Mapping, Optional, Sequence, Set, Tuple, Iterator, Union
from .config_getter import ConfigGetter

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


@dataclass
class NewSequenceEvent:
    """Entering a new Sequence"""

    path: [str | int, ...]


@dataclass
class DropContainerEvent:
    """Step out of Mapping or Sequence"""


WalkerEvent = NodeEvent | NewMappingEvent | NewSequenceEvent | DropContainerEvent


def objwalk(
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

    if _memo is None:
        _memo = set()

    if isinstance(obj, Mapping):
        if id(obj) not in _memo:
            _memo.add(id(obj))
            if not nodes_only:
                yield NewMappingEvent(_path)
            for key, value in obj.items():
                for child in objwalk(
                    value, _path=_path + (key,), _memo=_memo, nodes_only=nodes_only
                ):
                    yield child
            if not nodes_only:
                yield DropContainerEvent()

    elif isinstance(obj, (Sequence, Set)) and not isinstance(obj, str):
        if id(obj) not in _memo:
            _memo.add(id(obj))
            if not nodes_only:
                yield NewSequenceEvent(_path)
            for index, value in enumerate(obj):
                for child in objwalk(
                    value, _path=_path + (index,), _memo=_memo, nodes_only=nodes_only
                ):
                    yield child
            if not nodes_only:
                yield DropContainerEvent()

    else:
        yield NodeEvent(_path, obj)


def deep_update(
    obj: Mapping,
    updates: Mapping | None,
    create_missing: Union[callable, bool, dict] = True,
) -> Mapping:
    """Deep update the 'obj' with the leafs from 'updates

    :param obj: The dict that will be updated
    :param updates: The dict providing the values to update
    :param create_missing: If true, create any missing level.
    :return: the updated 'obj'
    """
    if not updates:
        return obj

    for event in objwalk(updates, nodes_only=True):
        ConfigGetter.set(obj, event.path, event.value, create_missing=create_missing)

    return obj

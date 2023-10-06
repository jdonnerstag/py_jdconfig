#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
"""

import logging
from typing import Mapping, Sequence
from .utils import NonStrSequence, ConfigException
from .objwalk import (
    ObjectWalker,
    NodeEvent,
    NewMappingEvent,
    NewSequenceEvent,
    DropContainerEvent,
)

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


class DeepUpdateMixin:
    """ """

    def __init__(self):
        pass

    def deep_update(self, obj: Mapping, updates: Mapping | None) -> Mapping:
        """Deep update the 'obj' with only the leafs from 'updates'. Create
        missing paths.

        :param obj: The dict that will be updated
        :param updates: The dict providing the values to update
        :param create_missing: If true, create any missing level.
        :return: the updated 'obj'
        """

        if not updates:
            return obj

        stack = [obj]
        any_elem = False
        gen = ObjectWalker.objwalk(updates, nodes_only=False)
        for event in gen:
            cur = stack[-1]

            key = None
            if event.path:
                key = event.path[-1]
                if key.endswith("[*]") and not isinstance(event, NewMappingEvent):
                    raise ConfigException(
                        f"'xyz[*]' syntax requires a value of type mapping: '{event.path}'"
                    )

            if any_elem:
                if not isinstance(cur, NonStrSequence):
                    raise ConfigException(
                        f"'xyz[*]' syntax is only allowed with lists: '{event.path}'"
                    )

                for elem in cur:
                    if isinstance(elem, Mapping) and key in elem:
                        stack.pop()
                        stack.append(elem)
                        cur = elem
                        break
                else:
                    raise ConfigException(f"Element does not exist: '{event.path}'")

                any_elem = False

            if isinstance(event, NewMappingEvent):
                if event.path:
                    if key.endswith("[*]"):
                        key = key[:-3]
                        any_elem = True
                        if not isinstance(cur, Mapping) or (key not in cur):
                            raise ConfigException(
                                "Config element does not exist: '{path}'"
                            )
                    elif (key not in cur) or not isinstance(cur[key], Mapping):
                        cur[key] = event.value
                        if not any_elem:
                            event.skip = True

                    stack.append(cur[key])
            elif isinstance(event, NewSequenceEvent):
                # TODO List in list?
                key = event.path[-1]
                if (
                    (key not in cur)
                    or not isinstance(cur[key], Sequence)
                    or isinstance(cur[key], str)
                ):
                    cur[key] = event.value
                    event.skip = True
                stack.append(cur[key])
            elif isinstance(event, NodeEvent):
                key = event.path[-1]
                cur[key] = event.value
            elif isinstance(event, DropContainerEvent):
                stack.pop()

        return obj

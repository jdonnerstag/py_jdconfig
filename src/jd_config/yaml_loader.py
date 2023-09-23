#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
A slightly extended version of yaml.SafeLoader. It extends the yaml values
(not the keys) with meta information about the yaml file, line and colum
(start and end position).

"""

import logging
from dataclasses import dataclass
from typing import Any
import yaml

__parent__name__ = __name__.rpartition('.')[0]
logger = logging.getLogger(__parent__name__)


@dataclass
class YamlObj:
    """Every yaml value will be replaced by a YamlObj, adding meta
    info such yaml file, line and column, to the actual yaml value.
    """

    line: int
    column: int
    file: str
    value: Any

    def replace(self, _old, _new):
        """Requires by pyyaml

        E.g. 1_000_000 => 1000000
        """

        return self.value.replace(_old, _new)

    def lower(self):
        """Convert the value to lowercase"""

        return self.value.lower()


@dataclass
class YamlContainer:
    """Base class for YamlMapping and YamlSequece"""

    # By means of the count, determine what is key and what value
    count: int

    def incr(self) -> int:
        """Increment the count"""

        self.count += 1
        return self.count

@dataclass
class YamlMapping(YamlContainer):
    "The parent container is YamlMapping"

@dataclass
class YamlSequence(YamlContainer):
    "The parent container is YamlSequence"


#pylint: disable=too-many-ancestors
class MyYamlLoader(yaml.SafeLoader):
    """A slightly extended version of yaml.SafeLoader. It extends the yaml values
    (not the keys) with meta information about the yaml file, line and colum
    (start and end position).
    """

    def __init__(self, stream) -> None:
        super().__init__(stream)

        # Remember the stack of Mappings and Sequences
        self.stack = []

    def construct_object(self, node, deep=False):
        obj = super().construct_object(node, deep)

        # If obj is a yaml value (and not a key), then wrap the value
        # into a YamlObj with file, line, and column meta into.
        if self.stack:
            last = self.stack[-1]
            last.incr()
            if isinstance(last, YamlSequence):
                return self.on_value(node, obj)

            if isinstance(last, YamlMapping) and (last.count & 1) == 0:
                return self.on_value(node, obj)

        return obj

    def on_value(self, node, obj) -> YamlObj:
        """Wrap the yaml value into a YamlObj with meta data, such as
        file, line and column
        """

        return YamlObj(
            node.start_mark.line + 1,
            node.start_mark.column + 1,
            node.start_mark.name,
            obj
        )

    def construct_sequence(self, node, deep=False):
        """Remember that the just started with a Sequence"""

        self.stack.append(YamlSequence(0))
        obj = super().construct_sequence(node, deep)
        self.stack.pop()
        return obj

    def construct_mapping(self, node, deep=False):
        """Remember that the just started with a Mapping"""

        self.stack.append(YamlMapping(0))
        obj = super().construct_mapping(node, deep)
        self.stack.pop()
        return obj
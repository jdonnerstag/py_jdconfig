#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import logging
from dataclasses import dataclass
from typing import Any
import yaml

logger = logging.getLogger(__name__)


@dataclass
class YamlObj:
    line: int
    column: int
    file: str
    value: Any

    def replace(self, _old, _new):
        return self.value.replace(_old, _new)

    def lower(self):
        return self.value.lower()


@dataclass
class YamlContainer:
    count: int

    def incr(self) -> int:
        self.count += 1
        return self.count

@dataclass
class YamlMapping(YamlContainer):
    pass

@dataclass
class YamlSequence(YamlContainer):
    pass

class MyYamlLoader(yaml.SafeLoader):

    def __init__(self, stream) -> None:
        super().__init__(stream)

        self.stack = []

    def construct_object(self, node, deep=False):
        obj = super().construct_object(node, deep)

        if self.stack:
            last = self.stack[-1]
            last.incr()
            if isinstance(last, YamlSequence):
                return self.on_value(node, obj)

            if isinstance(last, YamlMapping) and (last.count & 1) == 0:
                return self.on_value(node, obj)

        return obj

    def on_value(self, node, obj) -> YamlObj:
        return YamlObj(
            node.start_mark.line + 1,
            node.start_mark.column + 1,
            node.start_mark.name,
            obj
        )

    def construct_sequence(self, node, deep=False):
        self.stack.append(YamlSequence(0))
        obj = super().construct_sequence(node, deep)
        self.stack.pop()
        return obj

    def construct_mapping(self, node, deep=False):
        self.stack.append(YamlMapping(0))
        obj = super().construct_mapping(node, deep)
        self.stack.pop()
        return obj

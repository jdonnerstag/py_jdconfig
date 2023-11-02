#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
"""

from abc import ABC, abstractmethod
from enum import Enum
import logging
from types import GenericAlias, UnionType
from typing import Any, Type

from jd_config.utils import ConfigException


__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


class Handler(ABC):
    @abstractmethod
    def evaluate(self, value: Any, expected_type: Type, model) -> tuple[bool, Any]:
        return False, value

    @classmethod
    def is_generic(cls, expected_type: Type, origin: Type) -> bool:
        if not isinstance(expected_type, GenericAlias):
            return False

        return issubclass(expected_type.__origin__, origin)


class GenericListHandler(Handler):
    def evaluate(self, value: Any, expected_type: Type, model) -> tuple[bool, Any]:
        is_list_type = self.is_generic(expected_type, list)
        if is_list_type != isinstance(value, list):
            raise ConfigException(
                f"One is a list, the other is not: '{expected_type}' <> '{value}'"
            )

        if not is_list_type:
            return False, value

        list_type = expected_type.__args__[0]

        # The ConfigBaseModel is defined elsewhere. And if that subclass e.g. uses
        # a ForwardRef(), then get_type_hints() by default is not able to resolve it.
        # Hence: determine the module where the subclass (and ForwardRef) is defined,
        # and apply its globals() to be able to resolve ForwardRefs. Probably applies
        # to TypeVar, etc. as well.

        if isinstance(list_type, GenericAlias):
            raise ConfigException(f"Not yet supported: list of list: '{list_type}'")

        rtn = []
        for i, value in enumerate(value):
            value = model.validate_before(i, value, list_type)
            rtn.append(value)

        return True, rtn


class GenericDictHandler(Handler):
    def evaluate(self, value: Any, expected_type: Type, model) -> tuple[bool, Any]:
        if not self.is_generic(expected_type, dict):
            return False, value

        key_type, value_type = expected_type.__args__

        rtn = {}
        for key, elem in value.items():
            if key is not Any and not isinstance(key, key_type):
                raise ConfigException(
                    f"Wrong type: expected '{key_type}', found '{key}'"
                )

            elem = model.validate_before(key, elem, value_type)
            rtn[key] = elem

        return True, rtn


class EnumTypeHandler(Handler):
    def evaluate(self, value: Any, expected_type: Type, model) -> tuple[bool, Any]:
        if issubclass(expected_type, Enum):
            value = expected_type[value]
            return True, value

        return False, value


global_registry: list[Handler] = [
    GenericListHandler(),
    GenericDictHandler(),
    EnumTypeHandler(),
]

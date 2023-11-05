#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
A python runtime type checker.
"""

from dataclasses import dataclass
import dataclasses
import logging
from decimal import Decimal
from enum import Enum
from pathlib import Path
from types import GenericAlias, NoneType, UnionType
from typing import Any, Type, Optional, Callable, Literal

from typing_extensions import _AnnotatedAlias

from jd_config.utils import ConfigException


__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


class TypeCheckerException(ConfigException):
    """Data do not conform to a type"""


@dataclass
class TypeCheckerResult:
    match: bool
    value: Any
    type_: Type
    converters: list[Callable]

    def __bool__(self) -> bool:
        return self.match

    def __eq__(self, value: object) -> bool:
        if isinstance(value, bool):
            return self.match == value

        return False


def convert_enum(expected_type, value):
    if issubclass(expected_type, Enum):
        return expected_type[value]

    raise TypeCheckerException()


def convert_default(expected_type, value):
    # E.g. int(value), Path(value), ...
    return expected_type(value)


class TypeChecker:
    """I wish 'instanceof(xyz, <whatever type>)' would work for
    any type, but it doesn't.

    E.g. str, int, float, Decimal, list, dict, str|None, list[str]
    dict[str, str|int], Any, Optional, Union, Annotated, TypedDict, MyClass,
    and so on.

    Additionally, where types don't match, TypeChecker is able to convert
    the type, str -> int, dict to BaseModel, etc..
    """

    def __init__(self) -> None:
        self.converters = [convert_enum, convert_default]

    def instanceof(self, value, types, converters=None) -> TypeCheckerResult:
        if converters is None:
            converters = self.converters
        elif callable(converters):
            converters = [converters] + self.converters
        elif isinstance(converters, list):
            pass
        else:
            raise TypeCheckerException(
                f"Invalid 'converters' attribute: '{converters}'"
            )

        if isinstance(types, (list, tuple)):
            for elem_type in types:
                match = self.instanceof(value, elem_type, converters)
                if match:
                    return match

        rtn = TypeCheckerResult(False, value, types, converters)
        return self._value_isinstance(rtn)

    def _value_isinstance(self, rtn: TypeCheckerResult) -> TypeCheckerResult:
        """True, if value matches any of the expected types"""

        # If value matches any of the types, then we are done
        # Optional[x] is handled via __instanceof__. Unfortunately
        # not many types support this dunder already (python 3.11.2)

        if rtn.type_ is Any:
            rtn.match = True
            return rtn

        if rtn.value is None and rtn.type_ is NoneType:
            rtn.match = True
            return rtn

        try:
            if isinstance(rtn.value, rtn.type_):
                rtn.match = True
                return rtn
        except TypeError:
            pass

        if isinstance(rtn.type_, UnionType):
            for elem_type in rtn.type_.__args__:
                rtn2 = dataclasses.replace(rtn2, type_=elem_type)
                match = self._value_isinstance(rtn2)
                if match:
                    return match

        if isinstance(rtn.type_, _AnnotatedAlias):
            return self._validate_annotation(rtn)

        # Process containers, such as list and dict, by iterating over
        # all their elements (and recursively deep), and check the elements
        # against their (element) types. If not compliant, it'll raise an
        # exception.
        if isinstance(rtn.value, list):
            match = self.load_list_value(rtn)
            if match:
                return match
        elif isinstance(rtn.value, dict):
            match = self.load_dict_value(rtn)
            if match:
                return match

        rtn = self.convert(rtn)
        return rtn

    def _validate_annotation(self, rtn: TypeCheckerResult) -> TypeCheckerResult:
        """Validate 'Annotated[<type>, ...] types"""

        assert isinstance(rtn.type_, _AnnotatedAlias)

        for proc in rtn.type_.__metadata__:
            if not callable(proc):
                raise AttributeError(f"Annotation metadata must be callable: {proc}")

            rtn.value = proc(rtn.value)

        rtn.type_ = rtn.type_.__args__[0]

        return self._value_isinstance(rtn)

    @classmethod
    def is_generic(cls, expected_type: Type, origin: Type) -> bool:
        """True, if e.g. list[str], or dict[str, Any]"""
        if not isinstance(expected_type, GenericAlias):
            return False

        return issubclass(expected_type.__origin__, origin)

    def _get_container_type(self, value, expected_type, container_type, defaults):
        if self.is_generic(expected_type, container_type):
            rtn = expected_type.__args__[: len(defaults)]
        elif isinstance(expected_type, type) and (
            issubclass(expected_type, container_type)
        ):
            rtn = defaults
        else:
            raise TypeCheckerException(
                f"Types don't match: '{expected_type}' != '{value}'"
            )

        if not isinstance(value, container_type):
            raise TypeCheckerException(f"Expected a list, but found: '{value}'")

        return rtn

    def _iterate_union_type(self, value: Any, expected_type: UnionType) -> Any:
        for elem_type in expected_type.__args__:
            try:
                yield elem_type
            except:  # pylint: disable=bare-except
                pass

        raise TypeCheckerException(f"Types don't match: '{expected_type}' != '{value}'")

    def load_list_value(self, rtn: TypeCheckerResult) -> TypeCheckerResult:
        """Load input list values"""

        (elem_type,) = self._get_container_type(rtn.value, rtn.type_, list, (Any,))

        value = []
        for elem in rtn.value:
            rtn2 = dataclasses.replace(rtn, value=elem, type_=elem_type)
            match = self._value_isinstance(rtn2)
            if not match:
                return rtn
            value.append(match.value)

        rtn = dataclasses.replace(rtn, match=True, value=value)
        return rtn

    def load_dict_value(self, rtn: TypeCheckerResult) -> TypeCheckerResult:
        """Load input dict values"""

        key_type, elem_type = self._get_container_type(
            rtn.value, rtn.type_, dict, (Any, Any)
        )

        value = {}
        for key, elem in rtn.value.items():
            if key_type is not Any and not isinstance(key, key_type):
                raise TypeCheckerException(
                    f"Wrong type: expected '{key_type}', found '{key}'"
                )

            rtn2 = dataclasses.replace(rtn, value=elem, type_=elem_type)
            match = self._validate_annotation(rtn2)
            if not match:
                return rtn

            value[key] = match

        rtn = dataclasses.replace(rtn, match=True, value=value)
        return rtn

    def convert(self, rtn: TypeCheckerResult) -> TypeCheckerResult:
        """Some types can be automatically onverted"""
        for func in rtn.converters:
            try:
                rtn.value = func(rtn.type_, rtn.value)
                return rtn
            except:  # pylint: disable=bare-except
                pass

        return rtn

#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
A python runtime type checker.
"""

import dataclasses
import inspect
import logging
from dataclasses import dataclass
from enum import Enum
from types import GenericAlias, NoneType, UnionType
from typing import (
    Any,
    Callable,
    NewType,
    Type,
    _UnionGenericAlias,  # TODO Try to avoid/remove it
    get_args,
    get_origin,
)

from typing_extensions import _AnnotatedAlias  # TODO Try to avoid/remove it

from .utils import ConfigException

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


class TypeCheckerException(ConfigException):
    """Data do not conform to a type"""


# func(expected_type, value) -> <converted value or exception>
ConverterFn = Callable[[Type, Any], Any]


@dataclass
class TypeCheckerResult:
    """The TypeChecker result object"""

    # True, if the value matches the type
    match: bool

    # isinstance(<value>, ..)
    value: Any

    # The evaluated type. In case of a Union, the first
    # type that matched the value.
    type_: Type

    # TypeChecker supports converters. Converters are functions
    # which upon execution receive the expected type and the value.
    # The first converter that is successfully able to return a
    # value with the expected type, will "win". They are executed
    # in order of the list items.
    converters: list[ConverterFn] | None

    # Support constructs like 'if tc.isinstance(value, type_)'
    def __bool__(self) -> bool:
        return self.match

    # Support constructs like 'if tc.isinstance(value, type_) == False'
    def __eq__(self, value: object) -> bool:
        if isinstance(value, bool):
            return self.match == value

        return False


# ConverterFn
def convert_enum(expected_type: Type, value: Any) -> Any:
    """Create Enum from text (name)"""
    if issubclass(expected_type, Enum):
        return expected_type[value]

    raise TypeCheckerException()


# ConverterFn
def convert_default(expected_type: Type, value: Any) -> Any:
    """Default converter

    E.g. int(value), Path(value), ...
    """
    return expected_type(value)


class TypeChecker:
    """I wish 'instanceof(xyz, <whatever type>)' would work for
    any type, but it doesn't.

    E.g. str, int, float, Decimal, list, dict, str|None, list[str]
    dict[str, str|int], Any, Optional, Union, Annotated, Enum,
    TypedDict, MyClass, and so on.

    Additionally, where types don't match, TypeChecker can optionally
    try to convert the type, str -> int, dict to BaseModel, etc..
    """

    def __init__(self) -> None:
        # Default converters. Users may prepend additional ones.
        self.converters = [convert_enum, convert_default]

    def instanceof(
        self,
        value: Any,
        types: Type | tuple[Type, ...],
        converters: None | bool | list[ConverterFn] | ConverterFn = False,
    ) -> TypeCheckerResult:
        """An extended version of isinstance(), which aims to just work and do
        what a user probably expects from a function with this name. It
        tests (at runtime) a value against a type.

        And optionally, tries to convert the value to the expected type,
        applying converter functions.
        """
        if converters is None or converters is False:
            # Disable any converters
            converters = None
        elif converters is True:
            # Enable the default converters
            converters = self.converters
        elif callable(converters):
            # The converter provided, plus the default converters
            converters = [converters] + self.converters
        elif isinstance(converters, list):
            # Use the provided converter list, ignoring the default list.
            pass
        else:
            raise TypeCheckerException(
                f"Invalid 'converters' attribute: '{converters}'"
            )

        rtn = TypeCheckerResult(False, value, types, converters)

        # Like python default instanceof(), the 2nd argument can
        # be a tuple of types. The value gets evaluated against
        # all the types, until the first match is successfull.
        if isinstance(types, (list, tuple)):
            for elem_type in types:
                match = self.instanceof(value, elem_type, converters)
                if match:
                    return match

            return rtn

        return self._value_isinstance(rtn)

    def _value_isinstance(self, rtn: TypeCheckerResult) -> TypeCheckerResult:
        """True, if value matches any of the expected types"""

        # If value matches any of the types, then we are done
        # Optional[x] is handled via __instanceof__. Unfortunately
        # not many types support this dunder already (python 3.11.2)

        if rtn.type_ is Any:
            rtn.match = True
            return rtn

        if rtn.type_ is None:
            rtn.type_ = NoneType

        if rtn.type_ is NoneType:
            rtn.match = rtn.value is None
            return rtn

        if isinstance(rtn.type_, (UnionType, _UnionGenericAlias)):
            # 1st, without any Converter => exact match
            for elem_type in get_args(rtn.type_):
                rtn2 = dataclasses.replace(rtn, type_=elem_type, converters=None)
                match = self._value_isinstance(rtn2)
                if match:
                    return match

            # 2nd with converters
            if rtn.converters is not None:
                for elem_type in get_args(rtn.type_):
                    rtn2 = dataclasses.replace(rtn, type_=elem_type)
                    match = self._value_isinstance(rtn2)
                    if match:
                        return match

            return rtn

        # Must after evaluating Union
        if rtn.value is None:
            rtn.match = rtn.type_ is NoneType
            return rtn

        if isinstance(rtn.type_, NewType):
            rtn.type_ = rtn.type_.__supertype__

            try:
                if isinstance(rtn.value, rtn.type_):
                    rtn.match = True
                    return rtn
            except TypeError:
                pass

        try:
            if isinstance(rtn.value, rtn.type_):
                rtn.match = True
                return rtn
        except TypeError:
            pass

        if isinstance(rtn.type_, _AnnotatedAlias):
            return self._validate_annotation(rtn)

        # Process containers, such as list and dict, by iterating over
        # all their elements (and recursively deep), and check the elements
        # against their (element) types. If not compliant, it'll raise an
        # exception.
        try:
            if isinstance(rtn.value, list):
                match = self.check_list_value(rtn)
                if match:
                    return match
            elif isinstance(rtn.value, dict):
                match = self.check_dict_value(rtn)
                if match:
                    return match
        except TypeCheckerException:
            pass  # list or dict can not be loaded in expected type

        if rtn.converters:
            rtn = self.convert(rtn)

        return rtn

    def _validate_annotation(self, rtn: TypeCheckerResult) -> TypeCheckerResult:
        """Validate 'Annotated[<type>, ...] types"""

        assert isinstance(rtn.type_, _AnnotatedAlias)

        value = rtn.value
        try:
            for proc in rtn.type_.__metadata__:
                value = proc(value)
        except:  # pylint: disable=bare-except
            return rtn

        rtn.value = value
        rtn.type_ = get_args(rtn.type_)[0]

        return self._value_isinstance(rtn)

    @classmethod
    def is_generic_type_of(cls, tcr: TypeCheckerResult, container_type) -> bool:
        """True, no matter whether it is list or list[T]"""
        if isinstance(tcr.type_, GenericAlias):
            origin = get_origin(tcr.type_)
            return issubclass(origin, container_type)

        return issubclass(tcr.type_, container_type)

    def _get_container_type(self, tcr: TypeCheckerResult, container_type, defaults):
        if not self.is_generic_type_of(tcr, container_type):
            raise TypeCheckerException(f"Expected a '{container_type}', but found: '{tcr.type_}'")

        rtn = get_args(tcr.type_)
        if not rtn:
            rtn = defaults

        if not isinstance(tcr.value, container_type):
            raise TypeCheckerException(f"Expected a '{container_type}', but found: '{tcr.value}'")

        return rtn

    def check_list_value(self, rtn: TypeCheckerResult) -> TypeCheckerResult:
        """Load input list values"""

        (elem_type,) = self._get_container_type(rtn, list, (Any,))

        value = []
        types = set()
        for elem in rtn.value:
            rtn2 = dataclasses.replace(rtn, value=elem, type_=elem_type)
            match = self._value_isinstance(rtn2)
            if not match:
                return rtn
            value.append(match.value)
            types.add(match.type_)

        if get_args(rtn.type_) and len(types) > 0:
            if len(types) > 1:
                types = tuple(types)
                types = GenericAlias(UnionType, types)
            else:
                types = types.pop()

            rtn.type_ = GenericAlias(get_origin(rtn.type_), types)

        rtn = dataclasses.replace(rtn, match=True, value=value)
        return rtn

    def check_dict_value(self, rtn: TypeCheckerResult) -> TypeCheckerResult:
        """Load input dict values"""

        key_type, elem_type = self._get_container_type(rtn, dict, (Any, Any))

        # TypedDict's have annotations, but otherwise are just dicts
        type_hints = self.get_annotations(rtn.type_)

        value = {}
        key_types = set()
        value_types = set()
        for key, elem in rtn.value.items():
            rtn2 = dataclasses.replace(rtn, value=key, type_=key_type)
            match = self._value_isinstance(rtn2)
            if not match:
                return rtn

            key = match.value
            key_types.add(match.type_)

            # Apply the annotation, if one exists
            elem_type = type_hints.get(key, elem_type)

            rtn2 = dataclasses.replace(rtn, value=elem, type_=elem_type)
            match = self._value_isinstance(rtn2)
            if not match:
                return rtn

            elem = match.value
            value_types.add(match.type_)

            value[key] = elem

        if get_args(rtn.type_):
            rtn.type_ = GenericAlias(get_origin(rtn.type_), (key_types, value_types))

        rtn = dataclasses.replace(rtn, match=True, value=value)
        return rtn

    def convert(self, rtn: TypeCheckerResult) -> TypeCheckerResult:
        """Some types can be automatically onverted"""
        if isinstance(rtn.converters, (tuple, list)):
            for func in rtn.converters:
                try:
                    rtn.value = func(rtn.type_, rtn.value)
                    rtn.match = True
                    return rtn
                except:  # pylint: disable=bare-except
                    pass

        return rtn

    def get_annotations(self, type_: type):
        all_annotations = {}
        for cls in type_.mro():
            all_annotations.update(inspect.get_annotations(cls))

        return all_annotations

#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Inspired by pydantic, a BaseModel to flexibly load config data
into typed class attributes, and with validation.

Please see the readme file for reasons why this is not (yet)
build on top of pydantic.
"""

import dataclasses
import logging
import sys
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from pathlib import Path
from types import GenericAlias, UnionType
from typing import (
    Any,
    ClassVar,
    ForwardRef,
    Mapping,
    Optional,
    Self,
    Type,
    get_type_hints,
)

import yaml
from typing_extensions import _AnnotatedAlias

from jd_config.config_path import CfgPath, PathType
from jd_config.utils import DEFAULT, ConfigException, ContainerType, NonStrSequence

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)

BaseModel = ForwardRef("ConfigBaseModel")


class ValidationException(ConfigException):
    """Data do not conform to a type"""


@dataclass
class ModelFile:
    """Information about the (config) file, which was used to load
    the yaml, json, whatever data"""

    name: Path | None  # E.g. StringIO does not have a file name. # TODO Should allow URLs as well.
    data: Mapping  # The raw data as loaded from a file or url
    obj: BaseModel | None  # The model associated with the root of the file


@dataclass
class ModelMeta:
    """Model meta data"""

    # The (raw) input data that were used to load the model
    data: ContainerType
    # The parent model or None if its global root
    parent: BaseModel | None = None
    # The current path in the raw data, starting from global root
    path: CfgPath | None = None
    # The current file (e.g. a file imported from the global file)
    file: ModelFile | None = None
    # Globale file
    root: ModelFile | None = None

    # Some subclasses require static helpers. They can be made available via 'app'
    app: Any | None = None

    def __post_init__(self):
        if self.file is None:
            self.file = ModelFile(None, self.data, None)

        if self.root is None:
            self.root = self.file


def type_hints(cls) -> dict:
    """Get the type hints for all the user config attributes"""
    # The actual Model is defined elsewhere. And if that subclass e.g. uses
    # a ForwardRef(), then get_type_hints() by default is not able to resolve it.
    # Hence: determine the module where the subclass (and ForwardRef) is defined,
    # and apply its globals() to be able to resolve ForwardRefs. Probably applies
    # to TypeVar, etc. as well.
    mod_globals = sys.modules[cls.__module__].__dict__
    user_vars = get_type_hints(cls, include_extras=True, globalns=mod_globals)
    user_vars = {k: v for k, v in user_vars.items() if not k.startswith("_")}
    return user_vars


def input_names_map(cls) -> dict:
    """Create the mapping for input-names to model attribute names"""
    rtn = {}
    for key in cls.__type_hints__.keys():
        try:
            attr = cls.__dict__[key]
            rtn[attr.input_name] = attr.model_name
        except (KeyError, AttributeError):
            pass

    return rtn


class BaseModel:
    """BaseModel: This is the core class, which makes most things possible.

    Example:
    '''
    class MyModel(BaseModel):
        name: str
        email: Email | None
        homepage: URL | None
        version: Version
    '''

    BaseModel is very flexible and allows subclasses to easily extend it, e.g.
    'ResolvableBaseModel' allows to use "{ref: a}" or '{import: another_file.yaml}',
    still with type validation.
    """

    __type_hints__: ClassVar[dict] = None
    __input_names_map__: ClassVar[dict] = None

    def __init__(
        self,
        data: Optional[ContainerType] = None,
        parent: Optional[BaseModel] = None,
        *,
        meta: Optional[ModelMeta] = None,
    ) -> None:
        if parent is None and meta is None:
            meta = ModelMeta(app=None, parent=None, data=data, file=None, root=None)
        elif parent is not None:
            meta = dataclasses.replace(parent.__model_meta__, parent=parent, data=data)

        if meta.file.obj is None:
            meta.file.obj = self

        self.__model_meta__ = meta
        self.__extra_keys__ = None

        # It is IMPORTANT that the type hints and the name map are attached
        # to the user's subclass (and not BaseModel).
        cls = type(self)
        if cls.__type_hints__ is None:
            cls.__type_hints__ = type_hints(cls)

        if cls.__input_names_map__ is None:
            cls.__input_names_map__ = input_names_map(cls)

        self.load(meta.data)

    def load(self, data: ContainerType) -> Self:
        """Import the data previously loaded from json-, yaml, whereever,
        into the model."""
        if isinstance(data, Mapping):
            return self.load_map(data)
        if isinstance(data, NonStrSequence):
            pass  # TODO

        raise ConfigException(
            f"Data type not supported for loading: '{type(data)}' => '{data}'"
        )

    @classmethod
    def model_name(cls, input_name: str) -> str:
        """Get the model attribute name mapped to the input name"""
        return cls.__input_names_map__.get(input_name, input_name)

    def load_map(self, data: Mapping) -> Self:
        """Load dict type data into the model"""

        keys_set = []
        for input_key, value in data.items():
            model_key = self.model_name(input_key)

            if model_key not in self.__type_hints__:
                if self.__extra_keys__ is None:
                    self.__extra_keys__ = []
                self.__extra_keys__.append(input_key)
                continue

            expected_type = self.__type_hints__[model_key]
            value = self.load_item(input_key, value, model_key, expected_type)

            keys_set.append(model_key)
            setattr(self, model_key, value)

        self.validate_defaults(keys_set)
        self.validate_extra_keys(self.__extra_keys__)
        return self

    def load_item(self, key, value, model_key, expected_type) -> Any:
        """Process a single value from the input"""

        if isinstance(expected_type, _AnnotatedAlias):
            value, expected_type = self.process_annotations(value, expected_type)

        # Allow subclasses to make preprocess the input value
        value = self.validate_before(key, value, expected_type, model_key)

        # Process containers, such as list and dict, by iterating over
        # all their elements (and recursively deep), and check the elements
        # against their (element) types. If not compliant, it'll raise an
        # exception.
        if isinstance(value, list):
            try:
                value = self.load_list_value(value, expected_type)
                return value
            except ValidationException:
                pass
        elif isinstance(value, dict):
            try:
                value = self.load_dict_value(value, expected_type)
                return value
            except ValidationException:
                pass

        # If value matches any of the expected types, then we are done
        if self.value_isinstance(value, expected_type):
            return value

        # Else, iterate the expected types from left to right and try to
        # convert the value. If successful, we are done. Else raise an exception
        return self.try_to_convert(value, expected_type)

    def value_isinstance(self, value, expected_type) -> bool:
        """True, of value matches any of the expected types"""

        # If value matches any of the types, then we are done
        # Optional[x] is handled via __instanceof__. Unfortunately
        # not many types have this dunder yet (python 3.11.2)

        if expected_type is Any:
            return True

        try:
            if isinstance(value, expected_type):
                return True
        except TypeError:
            pass

        return False

    def process_annotations(self, value: Any, expected_type: _AnnotatedAlias) -> tuple:
        """Process all annotated types"""

        # Assume
        for proc in expected_type.__metadata__:
            if not callable(proc):
                raise AttributeError(f"Annotation metadata must be callable: {proc}")

            value = proc(value)

        expected_type = expected_type.__args__[0]

        return value, expected_type

    def validate_defaults(self, keys_set) -> None:
        """Validate that all fields have received a value or have defaults defined."""

        # Class variables with defaults defined are available in self.__class__.__dict__
        # TODO Does this work with subclasses which both have attributes???
        for key in self.__type_hints__.keys():
            # Already assigned a value??
            if key in keys_set:
                continue

            try:
                # Does it have a default value?
                # Should work for literal values as well as the Field descriptor
                getattr(self, key)
            except AttributeError:
                # pylint: disable=raise-missing-from
                raise ConfigException(
                    f"No value imported and no default value for attribute: '{key}'"
                )

    def validate_extra_keys(self, extra_keys) -> None:
        """Specify what to do with extra key/values available in the input, but
        don't have variables.

        By default, we do nothing. It is ok, that not all inputs have attributes.
        """

    def validate_before(
        self, key: str, value: any, expected_type, model_key: str
    ) -> Any:
        """Subclass may process the input, if some special logic is needed"""

        return value

    def try_to_convert(self, value, expected_type) -> Any:
        """Try to convert the value into any of the expected types"""
        if isinstance(expected_type, type):
            return self.convert(value, expected_type)

        if isinstance(expected_type, UnionType):
            for elem_type in expected_type.__args__:
                try:
                    value = self.convert(value, elem_type)
                    return value
                except:  # pylint: disable=bare-except
                    pass

        raise ValidationException(f"Types don't match: '{expected_type}' != '{value}'")

    def convert(self, value, expected_type) -> Any:
        """Some types can be automatically onverted"""
        if issubclass(expected_type, str):
            return str(value)
        if issubclass(expected_type, int):
            return int(value)
        if issubclass(expected_type, float):
            return float(value)
        if issubclass(expected_type, Decimal):
            return Decimal(value)
        if issubclass(expected_type, Path):
            return Path(value)
        if issubclass(expected_type, Enum):
            return expected_type[value]
        if issubclass(expected_type, BaseModel):
            return expected_type(value, self)

        raise ValidationException(f"Types don't match: '{expected_type}' != '{value}'")

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
            raise ValidationException(
                f"Types don't match: '{expected_type}' != '{value}'"
            )

        if not isinstance(value, container_type):
            raise ValidationException(f"Expected a list, but found: '{value}'")

        return rtn

    def _iterate_union_type(self, value: Any, expected_type: UnionType) -> Any:
        for elem_type in expected_type.__args__:
            try:
                yield elem_type
            except:  # pylint: disable=bare-except
                pass

        raise ValidationException(f"Types don't match: '{expected_type}' != '{value}'")

    def load_list_value(self, value, expected_type) -> Any:
        """Load input list values"""

        if isinstance(expected_type, UnionType):
            for elem_type in self._iterate_union_type(value, expected_type):
                value = self.load_list_value(value, elem_type)
                return value

        (elem_type,) = self._get_container_type(value, expected_type, list, (Any,))

        rtn = []
        for i, elem in enumerate(value):
            elem = self.load_item(i, elem, i, elem_type)
            rtn.append(elem)

        return rtn

    def load_dict_value(self, value, expected_type) -> Any:
        """Load input dict values"""

        if isinstance(expected_type, UnionType):
            for elem_type in self._iterate_union_type(value, expected_type):
                value = self.load_dict_value(value, elem_type)
                return value

        key_type, elem_type = self._get_container_type(
            value, expected_type, dict, (Any, Any)
        )

        rtn = {}
        for key, elem in value.items():
            if key_type is not Any and not isinstance(key, key_type):
                raise ValidationException(
                    f"Wrong type: expected '{key_type}', found '{key}'"
                )

            elem = self.load_item(key, elem, key, elem_type)
            rtn[key] = elem

        return rtn

    def __getitem__(self, key):
        # Allow to use model[key]
        return self.get(key)

    def get(self, path: PathType, default=DEFAULT) -> Any:
        """Deep get an attribute"""
        path = CfgPath(path)
        rtn = self
        elem = None
        try:
            for elem in path:
                if isinstance(rtn, Mapping):
                    rtn = rtn[elem]
                else:
                    rtn = getattr(rtn, elem)

            return rtn
        except:  # pylint: disable=bare-except
            pass

        if default != DEFAULT:
            return default

        raise KeyError(f"Key not found: '{elem}' in '{path}'")

    def to_dict(self) -> Mapping[str, Any]:
        """Recursively create a dict from the model"""
        rtn = {}
        for key in getattr(self, "__annotations__").keys():
            if key.startswith("_"):
                continue

            value = getattr(self, key)
            if hasattr(value, "to_dict"):
                value = value.to_dict()

            rtn[key] = value

        return rtn

    def to_yaml(self, stream, **kvargs):
        """Recursively export the model into a yaml"""
        data = self.to_dict()
        yaml.dump(data, stream, **kvargs)

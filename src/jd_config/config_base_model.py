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
from typing import (
    Any,
    ClassVar,
    ForwardRef,
    Mapping,
    Optional,
    Self,
    get_type_hints,
)

import yaml

from .config_path import CfgPath, PathType
from .utils import DEFAULT, ConfigException, ContainerType, NonStrSequence
from .type_checker import TypeChecker, TypeCheckerException, TypeCheckerResult

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


class BaseModel(TypeChecker):
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
        meta: Optional[ModelMeta] = None,
    ) -> None:
        TypeChecker.__init__(self)

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
            value = self.load_item(value, expected_type)

            keys_set.append(model_key)
            setattr(self, model_key, value)

        self.validate_defaults(keys_set)
        self.validate_extra_keys(self.__extra_keys__)
        return self

    def load_item(self, value, expected_type) -> Any:
        """Process a single value from the input"""

        res = self.instanceof(value, expected_type, converters=True)
        if not res:
            raise ValidationException(
                f"Types don't match: '{expected_type}' != '{value}'"
            )

        return res.value

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
                value = getattr(self, key)

                expected_type = type(self).__type_hints__[key]
                rtn = self.instanceof(value, expected_type, converters=True)
                if rtn:
                    setattr(self, key, rtn.value)

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

    # @override
    def convert(self, rtn: TypeCheckerResult) -> TypeCheckerResult:
        """Some types can be automatically onverted"""
        expected_type = rtn.type_
        value = rtn.value

        if issubclass(expected_type, Enum):
            rtn.value = expected_type[value]
        elif issubclass(expected_type, BaseModel):
            rtn.value = expected_type(value, self)
        elif self.is_generic_type_of(rtn, list) and (
            isinstance(value, (str, bytes))
        ):
            return rtn  # We are NOT converting strings into list of chars.
        else:
            try:
                rtn.value = expected_type(value)
            except:  # pylint: disable=bare-except
                return rtn

        rtn.match = True
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

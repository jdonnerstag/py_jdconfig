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
from pathlib import Path
from types import GenericAlias, NoneType, UnionType
from typing import Any, ForwardRef, Mapping, Optional, Self, Type, get_type_hints
from enum import Enum

import yaml
from typing_extensions import _AnnotatedAlias

from jd_config.config_path import CfgPath, PathType
from jd_config.field import Field
from jd_config.utils import DEFAULT, ConfigException, ContainerType, NonStrSequence

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)

ConfigBaseModel = ForwardRef("ConfigBaseModel")


class ValidationException(ConfigException):
    """Data do not conform to a type"""


@dataclass
class ConfigFile:
    """Information about a config file"""

    fname: Path | None  # E.g. StringIO does not have a file name.
    data: Mapping  # Raw data as loaded from file
    obj: ConfigBaseModel | None  # The model associated with the root of the file


@dataclass
class ConfigMeta:
    """Config meta data"""

    data: ContainerType  # Current data as loaded from file
    parent: ConfigBaseModel | None = None  # The parent model or None if its global root
    path: CfgPath | None = None  # The current path in the raw data

    file: ConfigFile | None = None  # Current file (e.g. imported)
    root: ConfigFile | None = None  # Globale file

    # Some subclasses require static helpers. They can be made available via 'app'
    app: Any | None = None

    def __post_init__(self):
        if self.file is None:
            self.file = ConfigFile(None, self.data, None)

        if self.root is None:
            self.root = self.file


class ConfigBaseModel:
    """The base model for every config data class"""

    __cfg_meta__: ConfigMeta

    def __init__(
        self,
        data: Optional[ContainerType] = None,
        parent: Optional[ConfigBaseModel] = None,
        *,
        meta: Optional[ConfigMeta] = None,
    ) -> None:
        if parent is None and meta is None:
            self.__cfg_meta__ = ConfigMeta(
                app=None, parent=None, data=data, file=None, root=None
            )
        elif parent is not None:
            self.__cfg_meta__ = dataclasses.replace(
                parent.__cfg_meta__, parent=parent, data=data
            )
        elif meta is not None:
            self.__cfg_meta__ = meta

        if self.__cfg_meta__.file.obj is None:
            self.__cfg_meta__.file.obj = self

        self.extra_keys = None
        self.load(self.__cfg_meta__.data)

    def load(self, data: ContainerType):
        """Load the config data from json-, yaml-files, whereever"""
        if isinstance(data, Mapping):
            return self.load_map(data)
        if isinstance(data, NonStrSequence):
            pass

        raise ConfigException(f"Expected a maps or list to load: '{data}'")

    @classmethod
    def type_hints(cls):
        """Get the type hint all the user config attributes"""
        # The ConfigBaseModel is defined elsewhere. And if that subclass e.g. uses
        # a ForwardRef(), then get_type_hints() by default is not able to resolve it.
        # Hence: determine the module where the subclass (and ForwardRef) is defined,
        # and apply its globals() to be able to resolve ForwardRefs. Probably applies
        # to TypeVar, etc. as well.
        mod_globals = sys.modules[cls.__module__].__dict__
        user_vars = get_type_hints(cls, include_extras=True, globalns=mod_globals)
        user_vars = {k: v for k, v in user_vars.items() if not k.startswith("_")}
        return user_vars

    @classmethod
    def model_name(cls, input_name):
        """Determine the class attribute name from the input name"""
        for attr, value in cls.__dict__.items():
            if attr.startswith("_"):
                continue
            if isinstance(value, Field):
                if value.input_name == input_name:
                    return attr
            elif attr == input_name:
                return attr

        return input_name

    def load_map(self, data: Mapping) -> Self:
        """Load the config data from json-, yaml-files, whereever"""

        user_vars = self.type_hints()

        keys_set = []
        for input_key, value in data.items():
            model_key = self.model_name(input_key)
            if model_key not in user_vars:
                if self.extra_keys is None:
                    self.extra_keys = []
                self.extra_keys.append(input_key)
                continue

            expected_type = user_vars[model_key]
            value = self.process_key(input_key, value, model_key, expected_type)

            keys_set.append(model_key)
            setattr(self, model_key, value)

        self.validate_defaults(user_vars, keys_set)
        self.validate_extra_keys(self.extra_keys)
        return self

    @classmethod
    def is_none_type(cls, expected_type) -> bool:
        """True, if is NoneType"""
        return isinstance(expected_type, type) and issubclass(expected_type, NoneType)

    def process_key(self, key, value, model_key, expected_type):
        """Process a single value"""

        value, expected_type = self.process_annotations(model_key, value, expected_type)

        value = self.validate_before(key, value, expected_type, model_key)

        # Process containers, such as list and dict, by iterating over
        # all their elements (and recursively deep), and check the elements
        # against their (element) types. If not compliant, it'll raise an
        # exception.
        if isinstance(value, list):
            try:
                value = self.process_list_value(value, expected_type)
                return value
            except:  # pylint:disable=bare-except
                pass
        elif isinstance(value, dict):
            try:
                value = self.process_dict_value(value, expected_type)
                return value
            except:  # pylint:disable=bare-except
                pass

        # If value matches any of the types, then we are done
        if self.value_isinstance(value, expected_type):
            return value

        # Else, move left to right and try to convert. If successful, we are done
        return self.try_to_convert(value, expected_type)

    def value_isinstance(self, value, expected_type) -> bool:
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

    def try_to_convert(self, value, expected_type):
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

    def process_annotations(self, key, value, expected_type):
        """Process all annotated types"""
        # We first process Annotated[..] types
        if not isinstance(expected_type, _AnnotatedAlias):
            return value, expected_type

        for proc in expected_type.__metadata__:
            value = proc(value)

        expected_type = expected_type.__args__[0]

        return value, expected_type

    def validate_defaults(self, user_vars, keys_set):
        """Validate that all fields have received a value or have defaults defined."""
        # Variables with defaults defined are available in self.__class__.dict
        # TODO Does this work with subclasses which both have attributes???
        for key in user_vars.keys():
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

    def validate_extra_keys(self, extra_keys):
        """Specify what to do with extra key/values available in the input, but
        don't have variables"""
        # TODO test against Optional and "| None" types
        pass
        # pylint: disable=raise-missing-from
        # raise ConfigException(f"No value imported for attribute: '{key}'")

    def validate_before(self, key, value, expected_type, model_key=None, *, idx=None):
        """Parse and convert the value. Do any preprocessing necessary."""

        if expected_type is Any:
            return value

        if value is None:
            return value

        # Lists etc.
        if isinstance(expected_type, GenericAlias):
            return value

        # This also works with Optional[xyz]. See __instancecheck__
        try:
            if isinstance(value, expected_type):
                return value
        except TypeError:
            pass

        if (isinstance(expected_type, type)) and (
            issubclass(expected_type, ConfigBaseModel)
        ):
            return expected_type(value, self)

        return value

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

        raise ValidationException(f"Types don't match: '{expected_type}' != '{value}'")

    @classmethod
    def is_generic(cls, expected_type: Type, origin: Type) -> bool:
        if not isinstance(expected_type, GenericAlias):
            return False

        return issubclass(expected_type.__origin__, origin)

    def process_list_value(self, value, expected_type):
        if self.is_generic(expected_type, list):
            elem_type = expected_type.__args__[0]
        elif isinstance(expected_type, type) and issubclass(expected_type, list):
            elem_type = Any
        elif isinstance(expected_type, UnionType):
            for elem_type in expected_type.__args__:
                try:
                    value = self.process_list_value(value, elem_type)
                    return value
                except:  # pylint: disable=bare-except
                    pass

            raise ValidationException(
                f"Types don't match: '{expected_type}' != '{value}'"
            )
        else:
            raise ValidationException(
                f"Types don't match: '{expected_type}' != '{value}'"
            )

        if not isinstance(value, list):
            raise ValidationException(f"Expected a list, but found: '{value}'")

        rtn = []
        for i, elem in enumerate(value):
            elem = self.process_key(i, elem, i, elem_type)
            rtn.append(elem)

        return rtn

    def process_dict_value(self, value, expected_type):
        if self.is_generic(expected_type, dict):
            key_type, elem_type = expected_type.__args__
        elif isinstance(expected_type, type) and issubclass(expected_type, dict):
            key_type, elem_type = Any, Any
        elif isinstance(expected_type, UnionType):
            for elem_type in expected_type.__args__:
                try:
                    value = self.process_dict_value(value, elem_type)
                    return value
                except:  # pylint: disable=bare-except
                    pass

            raise ValidationException(
                f"Types don't match: '{expected_type}' != '{value}'"
            )
        else:
            raise ValidationException(
                f"Types don't match: '{expected_type}' != '{value}'"
            )

        if not isinstance(value, dict):
            raise ValidationException(f"Expected a dict, but found: '{value}'")

        rtn = {}
        for key, elem in value.items():
            if key_type is not Any and not isinstance(key, key_type):
                raise ValidationException(
                    f"Wrong type: expected '{key_type}', found '{key}'"
                )

            elem = self.process_key(key, elem, key, elem_type)
            rtn[key] = elem

        return rtn

    def __getitem__(self, key):
        return self.get(key)

    def get(self, path: PathType, default=DEFAULT) -> Any:
        """Deep get an attribute"""
        path = CfgPath(path)
        rtn = self
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

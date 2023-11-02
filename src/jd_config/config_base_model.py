#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Inspired by pydantic, a BaseModel for classes holding config data.
"""

import dataclasses
import logging
import sys
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from types import GenericAlias, UnionType
from typing import Any, ForwardRef, Mapping, Optional, Self, get_type_hints

import yaml
from typing_extensions import _AnnotatedAlias

from jd_config import handler
from jd_config.config_path import CfgPath
from jd_config.field import Field
from jd_config.utils import ConfigException, ContainerType, NonStrSequence

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)

ConfigBaseModel = ForwardRef("ConfigBaseModel")


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

        # The ConfigBaseModel is defined elsewhere. And if that subclass e.g. uses
        # a ForwardRef(), then get_type_hints() by default is not able to resolve it.
        # Hence: determine the module where the subclass (and ForwardRef) is defined,
        # and apply its globals() to be able to resolve ForwardRefs. Probably applies
        # to TypeVar, etc. as well.
        user_vars = self.type_hints()

        keys_set = []
        for input_key, value in data.items():
            model_key = self.model_name(input_key)
            if model_key not in user_vars:
                if self.extra_keys is None:
                    self.extra_keys = []
                self.extra_keys.append(input_key)
                continue

            types = user_vars[model_key]
            types = self._expected_type_to_list(types)
            value = self.process_key(input_key, value, model_key, types)

            keys_set.append(model_key)
            setattr(self, model_key, value)

        self.validate_defaults(user_vars, keys_set)
        self.validate_extra_keys(self.extra_keys)
        return self

    def process_key(self, key, value, model_key, types):
        """Process a single value"""
        for expected_type in types:
            value = self.process_key_and_type(key, value, expected_type, model_key)

        return value

    def process_key_and_type(self, key, value, expected_type, model_key):
        """Process a single value and one of the expected types (if multiple)"""

        value, expected_type = self.process_annotations(model_key, value, expected_type)

        # Then we apply the handlers
        value = self.process_handlers(value, expected_type)

        # All the standard type converters
        value = self.validate_before(key, value, expected_type, model_key)
        return value

    def process_handlers(self, value, expected_type):
        """All the handlers to the value"""
        for entry in handler.global_registry:
            match, value = entry.evaluate(value, expected_type, self)
            if match:
                break

        return value

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
        user_vars = self.type_hints()

        for key in user_vars.keys():
            if key in keys_set:
                continue

            try:
                # Should work for literal values as well as the Field descriptor
                return self.__class__.__dict__[key]
            except KeyError:
                # pylint: disable=raise-missing-from
                raise ConfigException(f"No value imported for attribute: '{key}'")

    def validate_extra_keys(self, extra_keys):
        """Specify what to do with extra key/values available in the input, but
        don't have variables"""
        pass

    def validate_before(self, key, value, expected_type, model_key=None, *, idx=None):
        """Parse and convert the value. Do any preprocessing necessary."""

        if expected_type is Any:
            return value

        # Lists etc.
        if isinstance(expected_type, GenericAlias):
            return value

        # If UnionType, then return the first ones that does not fail with
        # an exception
        if isinstance(expected_type, UnionType):
            for type_ in expected_type.__args__:
                try:
                    return self.validate_before(key, value, type_, model_key, idx=idx)
                except:  # pylint: disable=bare-except
                    pass

            raise ConfigException(
                f"None of the Union types does match: '{expected_type}' != '{value}'"
            )

        if isinstance(value, expected_type):
            return value

        if issubclass(expected_type, ConfigBaseModel):
            return expected_type(value, self)

        if not isinstance(value, expected_type):
            value = self.convert(value, expected_type)

        if isinstance(value, expected_type):
            return value

        raise ConfigException(f"Types don't match: '{expected_type}' != '{value}'")

    def _expected_type_to_list(self, expected_type) -> tuple:
        if isinstance(expected_type, UnionType):
            return expected_type.__args__

        return (expected_type,)

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

        return value

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

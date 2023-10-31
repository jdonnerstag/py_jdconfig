#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
"""

import dataclasses
from dataclasses import dataclass
from decimal import Decimal
import sys
import logging
from pathlib import Path
from types import GenericAlias
from typing import Any, Mapping, Self, ForwardRef, get_type_hints
from typing_extensions import _AnnotatedAlias
from jd_config.config_path import CfgPath

from jd_config.utils import ConfigException, ContainerType, NonStrSequence
from jd_config import handler

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)

ConfigBaseModel = ForwardRef("ConfigBaseModel")


@dataclass
class ConfigFile:
    fname: Path | None  # E.g. StringIO does not have a file name.
    data: Mapping  # Raw data as loaded from file
    obj: ConfigBaseModel | None  # The model associated with the root of the file


@dataclass
class ConfigMeta:
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
    """xxx"""

    __cfg_meta__: ConfigMeta

    def __init__(
        self,
        data: ContainerType | None = None,
        parent: ConfigBaseModel | None = None,
        *,
        meta: ConfigMeta | None = None,
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
        if isinstance(data, Mapping):
            return self.load_map(data)
        if isinstance(data, NonStrSequence):
            pass

        raise ConfigException(f"Expected a maps or list to load: '{data}'")

    @classmethod
    def type_hints(cls):
        mod_globals = sys.modules[cls.__module__].__dict__
        user_vars = get_type_hints(cls, include_extras=True, globalns=mod_globals)
        user_vars = {k: v for k, v in user_vars.items() if not k.startswith("_")}
        return user_vars

    def load_map(self, data: Mapping) -> Self:
        # The ConfigBaseModel is defined elsewhere. And if that subclass e.g. uses
        # a ForwardRef(), then get_type_hints() by default is not able to resolve it.
        # Hence: determine the module where the subclass (and ForwardRef) is defined,
        # and apply its globals() to be able to resolve ForwardRefs. Probably applies
        # to TypeVar, etc. as well.
        user_vars = self.type_hints()

        keys_set = []
        for key, value in data.items():  # TODO What about lists?
            if key not in user_vars:
                if self.extra_keys is None:
                    self.extra_keys = []
                self.extra_keys.append(key)
                continue

            expected_type = user_vars[key]

            value, expected_type = self.pre_process(key, value, expected_type)

            # Then we apply the handler, until the first ones matches
            for entry in handler.global_registry:
                match, value = entry.evaluate(value, expected_type, self)
                if match:
                    break

            value = self.validate_before(key, value, expected_type)

            keys_set.append(key)
            setattr(self, key, value)

        self.validate_defaults(user_vars, keys_set)
        self.validate_extra_keys(self.extra_keys)
        return self

    def pre_process(self, key, value, expected_type):
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
            if key in keys_set:
                continue

            if key not in self.__class__.__dict__:
                raise ConfigException(f"No value imported for attribute: '{key}'")

    def validate_extra_keys(self, extra_keys):
        """Specify what to do with extra key/values available in the input, but
        don't have variables"""
        pass

    def validate_before(self, key, value, expected_type, *, idx=None):
        """Parse and convert the value. Do any preprocessing necessary."""
        if expected_type is Any:
            return value

        if issubclass(expected_type, ConfigBaseModel):
            return expected_type(value, self)

        # Lists etc.
        if isinstance(expected_type, GenericAlias):
            return value

        if not isinstance(value, expected_type):
            value = self.convert(value, expected_type)

        if not isinstance(value, expected_type):
            raise ConfigException(f"Types don't match: '{expected_type}' != '{value}'")

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

        return value

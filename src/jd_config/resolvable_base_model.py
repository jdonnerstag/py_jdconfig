#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
"""

import logging
from typing import Any, Type
from jd_config.config_base_model import ConfigBaseModel
from jd_config.placeholders import Placeholder
from jd_config.utils import ConfigException


__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


class MissingConfigException(ConfigException):
    """'???' denotes a mandatory value. Must be defined in an overlay."""


class ResolvableBaseModel(ConfigBaseModel):
    """xxx"""

    @classmethod
    def has_placeholder(cls, value) -> bool:
        return isinstance(value, str) and value.find("{") != -1

    def __getattribute__(self, key: str) -> Any:
        value = super().__getattribute__(key)
        if key.startswith("_"):
            return value

        if key not in self.__annotations__:
            return value

        type_hints = self.type_hints()
        expected_type = type_hints[key]

        if self.has_placeholder(value):
            value = self.analyze(key, value, expected_type)
        else:
            value = self.validate_before(key, value, expected_type)

        if value == "???":
            raise MissingConfigException(f"Mandatory config value missing: '{key}'")

        return value

    def validate_before(self, key, value, expected_type, *, idx=None):
        if self.has_placeholder(value):
            return value

        return super().validate_before(key, value, expected_type, idx=idx)

    def analyze(self, key, value, expected_type):
        while self.has_placeholder(value):
            value = self.resolve(value, expected_type)

        # value, expected_type = self.model.pre_process(key, value, expected_type)
        return value

    def parse_value(self, value):
        assert self.__cfg_meta__.app
        app = self.__cfg_meta__.app

        assert app.value_reader
        return list(app.value_reader.parse(value))

    def resolve(self, value: Any, expected_type: Type) -> Any:
        """Lazily resolve Placeholders

        Yaml values may contain our Placeholder. Upon loading a yaml file,
        a list will be created, for every yaml value that contains
        a Placeholder. resolve() lazily resolves the placeholders and joins
        the pieces together for the actuall yaml value.
        """

        if isinstance(value, str) and value.find("{") != -1:
            value = self.parse_value(value)

        if isinstance(value, list) and len(value) == 1:
            value = value[0]

        if isinstance(value, Placeholder):
            logger.debug("resolve(%s)", value)
            placeholder = value
            # if placeholder.memo_relevant():
            #    if placeholder in memo:
            #        raise ConfigException("Recursion ...")
            #
            #    memo.append(placeholder)
            value = placeholder.resolve(self, expected_type)

        if isinstance(value, list):
            value = [self.resolve(x, expected_type) for x in value]
            value = "".join(value)
            return value

        return value

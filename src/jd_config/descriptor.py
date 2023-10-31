#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
"""

import logging
from typing import Any, Type
from jd_config.config_base_model import ConfigBaseModel
from jd_config.placeholders import Placeholder
from jd_config.resolver_mixin import MissingConfigException
from jd_config.utils import ConfigException

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


class ConfigDescriptor:
    """Lazy resolve a variable"""

    def __init__(self) -> None:
        self.var_name: str | None = None  # The variable name
        self.value: Any | None = None
        self.model: ConfigBaseModel|None = None

    def __set_name__(self, owner, name):
        self.var_name = name

    def __get__(self, obj, objtype=None):
        self.model = model = obj
        assert isinstance(model, ConfigBaseModel)

        type_hints = model.type_hints()
        expected_type = type_hints[self.var_name]

        rtn = self.analyze(self.var_name, self.value, expected_type)
        return rtn

    def __set__(self, obj, value):
        self.value = value

    @property
    def meta(self):
        return self.model.__cfg_meta__

    @property
    def app(self):
        return self.meta.app

    @property
    def value_reader(self):
        return self.app.value_reader

    def parse_value(self, value: str):
        return list(self.value_reader.parse(value))

    def analyze(self, key, value, expected_type):
        while isinstance(value, str) and value.find("{") != -1:
            value = self.resolve(value)

        if value == "???":
            raise MissingConfigException(f"Mandatory config value missing: '{key}'")

        value, expected_type = self.model.pre_process(key, value, expected_type)
        return value

    def resolve(self, value: Any) -> Any:
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
            #    ctx.add_memo(placeholder)
            value = placeholder.resolve(self.model)

        if isinstance(value, list):
            value = [self.resolve(x) for x in value]
            value = "".join(value)
            return value

        return value

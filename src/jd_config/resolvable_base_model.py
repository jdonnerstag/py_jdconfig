#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
An extension to the BaseModel that support lazily resolution of placeholders
such as '{ref:db}' or '{import:myfile.yaml}'
"""

import dataclasses
import logging
from typing import Any, Optional, Type
from jd_config.config_base_model import BaseModel, ModelFile, ModelMeta
from jd_config.file_loader import ConfigFile
from jd_config.placeholders import Placeholder
from jd_config.utils import DEFAULT, ConfigException, ContainerType


__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


class MissingConfigException(ConfigException):
    """'???' denotes a mandatory value. Can either be defined in CLI or an overlay."""


class ResolvableBaseModel(BaseModel):
    """An extension to the BaseModel that support lazy resolution of placeholders
    such as '{ref:db}' or '{import:myfile.yaml}'
    """

    def __init__(
        self,
        data: Optional[ContainerType] = None,
        parent: Optional[BaseModel] = None,
        meta: Optional[ModelMeta] = None,
    ) -> None:
        self.__cached_values__ = None

        super().__init__(data, parent, meta)

    def new_meta(self, parent, data, **_kvargs):
        if parent is not None and isinstance(data, ConfigFile):
            file = ModelFile(name=data.file_1, data=data, obj=self)
            return super().new_meta(parent, data, file=file)

        return super().new_meta(parent, data)

    @classmethod
    def has_placeholder(cls, value) -> bool:
        """True if the input value contains a placeholder '{..}'"""
        return isinstance(value, str) and value.find("{") != -1

    def __getattribute__(self, key: str) -> Any:
        # We want to lazily resolve placeholders. Upon loading data,
        # we put the original string, e.g. '{ref:db}' into the attribute
        # (which often does not match the expected type). Only when accessing
        # the attribute, we resolve any optional placeholder. And only then
        # we validate the type.
        # Obviously lazily resolution can be slow, e.g. if the same attribute must
        # be resolved many times. model.to_dict() can be used resolve all attributes.
        # The resulting dict can again be used to load the model.

        # __geattribute__ is a little tricky. It is very easy to create
        # unwanted recursions, endlessly going in circles. I wish, we would not
        # need it.

        # Get the attribute. It must exist.
        value = super().__getattribute__(key)

        # User attributes must not start with a '_'
        if key.startswith("_"):
            return value

        # We are only interested in "our" attributes
        type_hints = type(self).__type_hints__
        # pylint: disable=unsupported-membership-test
        if type_hints is None or key not in type_hints:
            return value

        if self.has_placeholder(value):
            # Determine the expected type
            # pylint: disable=unsubscriptable-object
            expected_type = type_hints[key]
            value = self.analyze(key, value, expected_type)

        if value == "???":
            raise MissingConfigException(f"Mandatory config value missing: '{key}'")

        return value

    # @override
    def load_item(self, value, expected_type) -> Any:
        if self.has_placeholder(value):
            return value

        return super().load_item(value, expected_type)

    def analyze(self, _key, value, expected_type):
        """Upon accessing a user attribute, evaluate the stored value and
        resolve any placeholders"""

        while self.has_placeholder(value):
            value = self.resolve(value, expected_type)

        return value

    def parse_value(self, value):
        """Parse placeholders such as '{ref:}"""
        assert self.__model_meta__.app
        app = self.__model_meta__.app

        assert app.value_reader
        return list(app.value_reader.parse(value))

    def resolve(self, value: Any, expected_type: Type) -> Any:
        """Lazily resolve Placeholders

        Yaml values may contain our Placeholder. Upon loading a yaml file,
        a list will be created, for every yaml value that contains
        a Placeholder. resolve() lazily resolves the placeholders and joins
        the pieces together for the actuall yaml value.
        """

        if self.has_placeholder(value):
            value = self.parse_value(value)

        if isinstance(value, list) and len(value) == 1:
            value = value[0]

        if isinstance(value, Placeholder):
            logger.debug("resolve(%s)", value)
            placeholder = value
            value = placeholder.resolve(self, expected_type)

        if isinstance(value, list):
            value = [self.resolve(x, expected_type) for x in value]
            value = "".join(value)
            return value

        return value

#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Mixin to resolve preprocessed placeholders
"""

import logging
from typing import Any, Optional

from .deep_getter_base import GetterContext
from .placeholders import Placeholder
from .utils import ConfigException
from .value_reader import ValueReader

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


class ResolverMixin:
    """Mixin to resolve preprocessed placeholders

    Dependencies: None
    """

    def __init__(self, value_reader: Optional[ValueReader] = None) -> None:
        # Read string into Placeholders ...
        self.value_reader = ValueReader() if value_reader is None else value_reader

    def register_placeholder_handler(self, name: str, type_: type) -> None:
        """Register (add or replace) a placeholder handler"""

        self.value_reader.registry[name] = type_

    def resolve(self, value: Any, ctx: GetterContext) -> Any:
        """Lazily resolve Placeholders

        Yaml values may contain our Placeholder. Upon loading a yaml file,
        a list will be created, for every yaml value that contains
        a Placeholder. resolve() lazily resolves the placeholders and joins
        the pieces together for the actuall yaml value.
        """

        logger.debug("resolve(%s)", value)
        key = value

        if isinstance(value, list) and len(value) == 1:
            value = value[0]

        if isinstance(value, str) and value.find("{") != -1:
            registry = ctx.args.get("placeholder_registry", self.value_reader.registry)
            value = list(self.value_reader.parse(value, registry=registry))
            if len(value) == 1:
                value = value[0]

        if isinstance(value, Placeholder):
            placeholder = value
            ctx.add_memo(placeholder)
            value = placeholder.resolve(self, ctx)

        if isinstance(value, list):
            value = [self.resolve(x, ctx) for x in value]
            value = "".join(value)
            return value

        if value == "???":
            raise ConfigException(f"Mandatory config value missing: '{key}'")

        return value

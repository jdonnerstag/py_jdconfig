#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Extended standard dict like getter to also support deep paths, and also
search patterns, such as 'a..c', 'a.*.c'
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
    """Extended standard dict like getter to also support deep paths, and also
    search patterns, such as 'a..c', 'a.*.c'
    """

    def __init__(self, value_reader: Optional[ValueReader] = None) -> None:
        # Read string into Placeholders ...
        self.value_reader = ValueReader() if value_reader is None else value_reader

    def register_placeholder_handler(self, name: str, type_: type) -> None:
        """Register (add or replace) a placeholder handler"""

        self.value_reader.registry[name] = type_

    def cb_get(self, data, key, ctx) -> Any:
        """Retrieve the element. Subclasses may expand it, e.g. to resolve
        placeholders
        """
        value = super().cb_get(data, key, ctx)

        if not ctx.args or not ctx.args.get("skip_resolver", False):
            while isinstance(value, str) and value.find("{") != -1:
                value = list(self.value_reader.parse(value))
                value = self.resolve(value, ctx)

        if value == "???":
            raise ConfigException(f"Mandatory config value missing: '{ctx.cur_path()}'")

        return value

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
            value = list(self.value_reader.parse(value))
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

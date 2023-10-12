#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Extended standard dict like getter to also support deep paths, and also
search patterns, such as 'a..c', 'a.*.c'
"""

import logging
from typing import Any, Mapping, Optional
from jd_config.placeholders import Placeholder

from jd_config.value_reader import ValueReader

from .utils import ConfigException, NonStrSequence
from .deep_getter_base import DeepGetter, GetterContext

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


class ConfigResolveMixin:
    """Extended standard dict like getter to also support deep paths, and also
    search patterns, such as 'a..c', 'a.*.c'
    """

    def __init__(self, *_, **__) -> None:
        # Read string into Placeholders ...
        self.value_reader = ValueReader()

    def register_placeholder_handler(self, name: str, type_: type) -> None:
        """Register (add or replace) a placeholder handler"""

        self.value_reader.registry[name] = type_

    def cb_get_2_with_context(self, ctx: GetterContext) -> Any:
        """Retrieve the element. Subclasses may expand it, e.g. to resolve
        placeholders
        """
        value = super().cb_get_2_with_context(ctx)

        while isinstance(value, str) and value.find("{") != -1:
            value = list(self.value_reader.parse(value))
            value = self.resolve(ctx, value)

        if value == "???":
            raise ConfigException(f"Mandatory config value missing: '{ctx.cur_path()}'")

        return value

    def resolve(self, ctx: GetterContext, value: Any) -> Any:
        """Lazily resolve Placeholders

        Yaml values may contain our Placeholder. Upon loading a yaml file,
        a list will be created, for every yaml value that contains
        a Placeholder. resolve() lazily resolves the placeholders and joins
        the pieces together for the actuall yaml value.
        """

        # Used to detected recursions in resolving placeholders
        if ctx.memo is None:
            ctx.memo = []

        logger.debug("resolve(%s)", value)
        key = value

        if isinstance(value, list) and len(value) == 1:
            value = value[0]

        if isinstance(value, Placeholder):
            placeholder = value
            if placeholder in ctx.memo:
                ctx.memo.append(placeholder)
                raise RecursionError(f"Config recursion detected: {ctx.memo}")

            ctx.memo.append(placeholder)
            value = placeholder.resolve(self, ctx)

        if isinstance(value, list):
            value = [self.resolve(ctx, x) for x in value]
            value = "".join(value)
            return value

        if isinstance(value, str) and value.find("{") != -1:
            value = list(self.value_reader.parse(value))
            if len(value) == 1:
                value = value[0]
            value = self.resolve(ctx, value)

        if value == "???":
            raise ConfigException(f"Mandatory config value missing: '{key}'")

        return value

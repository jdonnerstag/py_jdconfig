#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Extended standard dict like getter to also support deep paths, and also
search patterns, such as 'a..c', 'a.*.c'
"""

import logging
from typing import Any
from jd_config.placeholders import Placeholder
from jd_config.resolver_mixin import ResolverMixin
from jd_config.value_reader import ValueReader
from .utils import ConfigException
from .deep_getter_base import GetterContext

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


class ConfigResolveMixin(ResolverMixin):
    """Extended standard dict like getter to also support deep paths, and also
    search patterns, such as 'a..c', 'a.*.c'
    """

    def cb_get(self, data, key, path, **kvargs) -> Any:
        """Retrieve the element. Subclasses may expand it, e.g. to resolve
        placeholders
        """
        value = super().cb_get(data, key, path)

        if "skip_resolver" not in kvargs:
            while isinstance(value, str) and value.find("{") != -1:
                value = list(self.value_reader.parse(value))
                value = self.resolve(value)

        if value == "???":
            raise ConfigException(f"Mandatory config value missing: '{path}'")

        return value

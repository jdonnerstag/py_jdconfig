#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Extended standard dict like getter to also support deep paths, and also
search patterns, such as 'a..c', 'a.*.c'
"""

import logging
from typing import Any

from .utils import ConfigException
from .resolver_mixin import ResolverMixin
from .deep_getter_base import GetterContext, GetterPlugin

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


class ConfigResolvePlugin(ResolverMixin, GetterPlugin):
    """Extended standard dict like getter to also support deep paths, and also
    search patterns, such as 'a..c', 'a.*.c'
    """

    def cb_get_2_with_context(self, ctx: GetterContext, value: Any, idx: int) -> Any:
        """Retrieve the element. Subclasses may expand it, e.g. to resolve
        placeholders
        """
        value = ctx.invoke_next(value, idx)

        while isinstance(value, str) and value.find("{") != -1:
            value = list(self.value_reader.parse(value))
            value = self.resolve(value, self._data, _memo=ctx.memo)

        if value == "???":
            raise ConfigException(f"Mandatory config value missing: '{ctx.cur_path()}'")

        return value

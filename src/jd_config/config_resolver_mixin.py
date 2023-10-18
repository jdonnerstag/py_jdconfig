#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Extended standard dict like getter to also support deep paths, and also
search patterns, such as 'a..c', 'a.*.c'
"""

import logging
from typing import Any, Optional

from .resolver_mixin import ResolverMixin
from .utils import ConfigException
from .value_reader import ValueReader

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


class ConfigResolveMixin(ResolverMixin):
    """Extended standard dict like getter to also support deep paths, and also
    search patterns, such as 'a..c', 'a.*.c'
    """

    def __init__(self, value_reader: Optional[ValueReader] = None) -> None:
        ResolverMixin.__init__(self, value_reader)

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

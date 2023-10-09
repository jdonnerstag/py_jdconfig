#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Extended standard dict like getter to also support deep paths, and also
search patterns, such as 'a..c', 'a.*.c'
"""

import logging
from typing import Any, Mapping

from .utils import ConfigException, NonStrSequence, PathType
from .deep_getter_base import GetterContext
from .deep_getter_with_search import DeepGetterWithSearch
from .resolver_mixin import ResolverMixin

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


class DeepGetterWithResolve(DeepGetterWithSearch, ResolverMixin):
    """Extended standard dict like getter to also support deep paths, and also
    search patterns, such as 'a..c', 'a.*.c'
    """

    def __init__(
        self, data: Mapping | NonStrSequence, path: PathType, *, _memo=()
    ) -> None:
        DeepGetterWithSearch.__init__(self, data, path, _memo=_memo)
        ResolverMixin.__init__(self)

    def cb_get_2_with_context(self, ctx: GetterContext) -> Any:
        """Retrieve the element. Subclasses may expand it, e.g. to resolve
        placeholders
        """
        value = super().cb_get_2_with_context(ctx)

        while isinstance(value, str) and value.find("{") != -1:
            value = list(self.value_reader.parse(value))
            value = self.resolve(value, self._data, _memo=ctx.memo)

        if value == "???":
            raise ConfigException(f"Mandatory config value missing: '{ctx.cur_path()}'")

        return value

#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Mixin to resolve preprocessed placeholders
"""

import logging
from typing import Any, Mapping, Optional
from .placeholders import Placeholder
from .value_reader import ValueReader
from .objwalk import ConfigException


__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


class ResolverMixin:
    """Mixin to resolve preprocessed placeholders

    Dependencies: None
    """

    def __init__(self) -> None:
        # Read string into Placeholders ...
        self.value_reader = ValueReader()

    def register_placeholder_handler(self, name: str, type_: type) -> None:
        """Register (add or replace) a placeholder handler"""

        self.value_reader.registry[name] = type_

    def resolve(
        self,
        value: Any,
        data: Optional[Mapping] = None,
        *,
        _memo: list | None = None,
    ) -> Any:
        """Lazily resolve Placeholders

        Yaml values may contain our Placeholder. Upon loading a yaml file,
        a list will be created, for every yaml value that contains
        a Placeholder. resolve() lazily resolves the placeholders and joins
        the pieces together for the actuall yaml value.
        """

        # Used to detected recursions in resolving placeholders
        if _memo is None:
            _memo = []

        logger.debug("resolve(%s)", value)
        key = value
        if isinstance(value, Placeholder):
            if value in _memo:
                _memo.append(value)
                raise ConfigException(f"Recursion detected: {_memo}")

            _memo.append(value)
            value = value.resolve(self, data, _memo=_memo)

        if isinstance(value, list):
            value = [self.resolve(x, data, _memo=_memo) for x in value]
            value = "".join(value)
            return value

        if isinstance(value, str) and value.find("{") != -1:
            value = list(self.value_reader.parse(value))
            if len(value) == 1:
                value = value[0]
            value = self.resolve(value, data, _memo=_memo)

        if value == "???":
            raise ConfigException(f"Mandatory config value missing: '{key}'")

        return value

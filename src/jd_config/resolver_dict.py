#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Upon retrieving a config value resolve optional placeholders.
"""

import logging
from typing import Any, Mapping, Optional
from .placeholders import Placeholder
from .value_reader import ValueReader
from .objwalk import ConfigException, NonStrSequence
from .dict_list import DictList

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)

DEFAULT = object()


class ResolverDictList(DictList):
    """Upon retrieving a config value resolve optional placeholders.

    Config consists of dict- and list-like nodes, and config values.
    Most values are either int, float, bool or strings. String value
    may contain placeholders, e.g. "{ref:db}". ResolverDictList wraps
    around dict- and list-like objects, and provides a method to get
    and resolve (if required) a value.
    """

    def __init__(
        self,
        obj: Mapping | NonStrSequence,
        path: list[str | int],
        value_reader: ValueReader = ValueReader(),
    ) -> None:
        super().__init__(obj)

        self.path = path

        # Read string into Placeholders ...
        self.value_reader = value_reader

    def register_placeholder_handler(self, name: str, type_: type) -> None:
        """Register (add or replace) a placeholder handler"""

        self.value_reader.registry[name] = type_

    def __getitem__(self, key: str | int) -> Any:
        rtn = self.obj[key]

        if isinstance(rtn, DictList):
            rtn = rtn.obj

        if isinstance(rtn, (Mapping, NonStrSequence)):
            rtn = ResolverDictList(rtn, self.path + [key], self.value_reader)

        return rtn

    def resolve(
        self,
        key: Any,
        data: Mapping,
        default: Any = DEFAULT,
    ) -> Any:
        """Lazily resolve Placeholders

        Yaml values may contain our Placeholder. Upon loading a yaml file,
        a list will be created, for every yaml value that contains
        a Placeholder. resolve() lazily resolves the placeholders and joins
        the pieces together for the actuall yaml value.
        """

        value = self.get(key, default)
        while isinstance(value, str) and value.find("{") != -1:
            value = list(self.value_reader.parse(value))
            value = self._resolve_inner(value, data)

        if value == "???":
            path = self.path + [key]
            raise ConfigException(f"Mandatory config value missing: '{path}'")

        return value

    def _resolve_inner(
        self,
        value: str,
        data: Mapping,
        *,
        _memo: list | None = None,
    ) -> Any:
        """Lazily resolve a config value"""

        # Detected recursions in resolving placeholders
        if _memo is None:
            _memo = []

        if len(value) == 1:
            value = value[0]

        if isinstance(value, Placeholder):
            if value in _memo:
                _memo.append(value)
                raise ConfigException(f"Recursion detected: {_memo}")

            _memo.append(value)
            value = value.resolve(self, data, _memo=_memo)

        elif isinstance(value, NonStrSequence):
            value = [self._resolve_inner(x, data, _memo=_memo) for x in value]
            value = "".join(value)

        return value

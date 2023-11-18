#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
A mixin that extends DeepGetter with a resolver. It resolves. e.g. 'a: {ref:b}'
such that the reference placeholder gets virtually (not physically) replaced
with the value from 'b'. Or 'a: {import:myfile.yaml}' which loads myfile.yaml
and makes the config available under 'a'.
"""

import logging
from typing import Any, Callable, Optional, Self

from jd_config.file_loader import ConfigFile

from .config_path import CfgPath
from .placeholders import Placeholder
from .utils import ConfigException, ContainerType
from .value_reader import ValueReader

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


class MissingConfigException(ConfigException):
    """'???' denotes a mandatory value. Must be defined in an overlay."""


class ResolverMixin:
    """A mixin that extends DeepGetter with a resolver. It resolves. e.g. 'a: {ref:b}'
    such that the reference placeholder gets virtually (not physically) replaced
    with the value from 'b'. Or 'a: {import:myfile.yaml}' which loads myfile.yaml
    and makes the config available under 'a'.
    """

    def __init__(
        self,
        data: ContainerType,
        path: Optional[CfgPath] = None,
        *,
        value_reader: Optional[ValueReader] = None,
        **kvargs,
    ) -> None:
        super().__init__(data, path, **kvargs)

        # ValueReader parses a yaml value and returns a list of literals
        # and placeholders.
        self.value_reader = ValueReader() if value_reader is None else value_reader
        self.skip_resolver = False

    def clone(self, data, key) -> Self:
        rtn = super().clone(data, key)
        rtn.value_reader = self.value_reader
        rtn.skip_resolver = self.skip_resolver
        rtn.is_local_root = isinstance(data, ConfigFile)
        return rtn

    def register_placeholder_handler(self, name: str, type_: type) -> None:
        """Register (add or replace) a placeholder handler"""

        self.value_reader.registry[name] = type_

    @classmethod
    def has_placeholder(cls, value) -> bool:
        return isinstance(value, str) and value.find("{") != -1

    # @override
    def _get(
        self,
        path: CfgPath,
        *,
        on_missing: Callable,
        resolve: bool = True,
        memo=None,
        **kvargs,
    ) -> (Any, CfgPath):
        """Retrieve the element. Subclasses may expand it, e.g. to resolve
        placeholders
        """
        if memo is None:
            memo = []

        value, rest_path = super()._get(
            path, on_missing=on_missing, memo=memo, **kvargs
        )

        if resolve:
            value = self.resolve(value, memo)

        if value == "???":
            cur_path = self.cur_path(path[0])
            raise MissingConfigException(
                f"Mandatory config value missing: '{cur_path}'"
            )

        return value, rest_path

    def resolve(self, value: Any, memo) -> Any:
        """Lazily resolve Placeholders"""

        if not self.skip_resolver:
            while self.has_placeholder(value):
                value = self.resolve_single(value, memo)

        return value

    def resolve_single(self, value: Any, memo) -> Any:
        """Lazily resolve Placeholders

        Yaml values may contain our Placeholder. Upon loading a yaml file,
        a list will be created, for every yaml value that contains
        a Placeholder. resolve() lazily resolves the placeholders and joins
        the pieces together for the actuall yaml value.
        """

        if isinstance(value, list) and len(value) == 1:
            value = value[0]

        if self.has_placeholder(value):
            value = list(self.value_reader.parse(value))
            if len(value) == 1:
                value = value[0]

        if isinstance(value, Placeholder):
            logger.debug("resolve(%s)", value)
            placeholder = value
            if placeholder.MEMO_RELEVANT:
                if placeholder in memo:
                    memo.append(placeholder)
                    raise ConfigException(f"Config recursion detected: {memo}")

                memo.append(placeholder)
            value = placeholder.resolve(self, memo)

        if isinstance(value, list):
            value = [self.resolve_single(x, memo) for x in value]
            value = "".join(value)
            return value

        return value

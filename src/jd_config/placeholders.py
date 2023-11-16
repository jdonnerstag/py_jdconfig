#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""Manage everything related to placeholders, such as
```
  db_engine: '{ref: db.engine, innodb}'
```

Placeholders can only occur in yaml values. They are not allowed in keys.
And it must be a yaml *string* value, surrounded by quotes.
"""

import dataclasses
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Mapping, Optional

from .config_path import CfgPath
from .deep_getter import DeepGetter
from .getter_context import GetterContext
from .utils import DEFAULT, ConfigException, ContainerType, new_trace

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


class PlaceholderException(ConfigException):
    """Placeholder exception"""


# pylint: disable=too-few-public-methods
class Placeholder(ABC):
    """A common base class for all Placeholders"""

    @abstractmethod
    def resolve(self, ctx: "GetterContext", resolver):
        """Resolve the placeholder"""

    def memo_relevant(self) -> bool:
        """If relevant for Placeholder recursion detection"""
        return True


LoaderType = Callable[[str], Mapping]


@dataclass
class ImportPlaceholder(Placeholder):
    """Import Placeholder: '{import: <file>[, <replace=False>]}'"""

    file: str
    cache: bool = field(default=True, repr=False)
    loader: Optional[LoaderType] = field(default=None, repr=False)

    def __post_init__(self):
        assert self.file
        if isinstance(self.file, (str, Path)):
            if Path(self.file).is_absolute():
                logger.warning("Absolut import file path detected: '%s'", self.file)

    def memo_relevant(self) -> bool:
        """Not relevant for Placeholder recursion detection"""
        return False

    def resolve(self, ctx: "GetterContext", resolver):
        file = resolver.resolve(self.file, ctx)

        assert (
            self.loader is not None
        ), "ImportPlaceholder: Bug. No file 'loader' configured"

        rtn = self.loader.load_import(file, cache=self.cache)
        ctx.current_file = rtn

        return rtn


@dataclass
class RefPlaceholder(Placeholder):
    """Reference Placeholder: '{ref: <path>[, <default>]}'"""

    path: str
    default_val: Any = None

    def __post_init__(self):
        assert self.path

    def resolve(self, ctx: "GetterContext", resolver):
        new_ctx = dataclasses.replace(ctx, data=ctx.current_file)
        path = CfgPath(self.path)
        if path and path[0] in [CfgPath.PARENT_DIR, CfgPath.CURRENT_DIR]:
            path = ctx.parent_path(0) + path

        return self._resolve_inner(ctx, new_ctx, path)

    def _resolve_inner(self, parent_ctx: "GetterContext", ctx: "GetterContext", path):
        try:
            getter = DeepGetter(ctx=ctx)
            value = getter.get(ctx, path)
            return value
        except (
            KeyError,
            IndexError,
            ConfigException,
        ) as exc:  # pylint: disable=bare-except  # noqa: E722
            if self.default_val is not None:
                return self.default_val

            if isinstance(exc, ConfigException):
                exc.trace.insert(0, new_trace(parent_ctx, self))
                raise exc

            raise PlaceholderException(
                f"Failed to resolve RefPlaceholder: '{self.path}'"
            ) from exc


ConfigFn = Callable[[], ContainerType]


@dataclass
class GlobalRefPlaceholder(RefPlaceholder):
    """Reference Placeholder: '{global: <path>[, <default>]}'

    ref and global are identical, except that the map they resolve
    against is different.
    """

    # The order of the arguments is: all the attributes from the parent(s)
    # class(es) first then those of the child class.
    root_cfg: Optional[ConfigFn] = field(default=None, repr=False)

    def resolve(self, ctx: "GetterContext", resolver):
        path = CfgPath(self.path)
        if path and path[0] in [CfgPath.PARENT_DIR, CfgPath.CURRENT_DIR]:
            raise ConfigException(
                f"Relativ config paths are not allowed with global refs: '{path}'"
            )

        new_ctx = dataclasses.replace(
            ctx, data=ctx.global_file, current_file=ctx.global_file
        )
        return self._resolve_inner(ctx, new_ctx, self.path)


class EnvvarConfigException(ConfigException):
    """EnvPlaceholder related exception"""


@dataclass
class EnvPlaceholder(Placeholder):
    """Environment Variable Placeholder: '{env: <env-var>[, <default>]}'"""

    env_var: str
    default_val: Any = DEFAULT

    def __post_init__(self):
        assert self.env_var

    def resolve(self, ctx, resolver) -> str:
        value = os.environ.get(self.env_var, self.default_val)
        if value is DEFAULT:
            raise EnvvarConfigException(
                f"Environment does not exist: '{self.env_var}'",
                trace=new_trace(ctx=ctx, placeholder=self),
            )

        return value


@dataclass
class TimestampPlaceholder(Placeholder):
    """Replace yaml value with timestamp: '{timestamp: <format>}'"""

    format: str

    def __post_init__(self):
        assert self.format

    def resolve(self, *_, **__) -> str:
        now = datetime.now()
        value = now.strftime(self.format)
        return value

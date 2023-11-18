#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""Manage everything related to placeholders, such as
```
  db_engine: '{ref: db.engine, innodb}'
```

Placeholders can only occur in yaml values. They are not allowed in keys.
And it must be a yaml *string* value, surrounded by quotes.
"""

import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, TYPE_CHECKING

from .utils import DEFAULT, ConfigException, ContainerType

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


if TYPE_CHECKING:
    from jd_config.resolver_mixin import ResolverMixin


class PlaceholderException(ConfigException):
    """Placeholder exception"""


# pylint: disable=too-few-public-methods
class Placeholder(ABC):
    """A common base class for all Placeholders"""

    MEMO_RELEVANT = False

    @abstractmethod
    def resolve(self, model: "ResolverMixin", memo: list):
        """Resolve the placeholder"""


LoaderType = Callable[[str], Mapping]
ConfigFn = Callable[[], ContainerType]


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

    def resolve(self, model: "ResolverMixin", memo: list):
        file = model.resolve(self.file, memo=[])

        assert (
            self.loader is not None
        ), "ImportPlaceholder: Bug. No file 'loader' configured"

        rtn = self.loader.load_import(file, parent=model, cache=self.cache)
        return rtn


@dataclass
class RefPlaceholder(Placeholder):
    """Reference Placeholder: '{ref: <path>[, <default>]}'"""

    path: str
    default_val: Any = None

    MEMO_RELEVANT = True

    def __post_init__(self):
        assert self.path

    def resolve(self, model: "ResolverMixin", memo: list):
        path = model.path_obj(self.path)
        if path.is_relativ():
            local_root = model
        else:
            local_root = model.get_local_root()

        return self._resolve_inner(local_root, path, memo)

    def _resolve_inner(self, local_root, path, memo):
        try:
            value = local_root.get(path, memo=memo)
            return value
        except KeyError as exc:
            if self.default_val is not None:
                return self.default_val

            if isinstance(exc, ConfigException):
                # exc.trace.insert(0, new_trace(parent_ctx, self))
                raise exc

            raise PlaceholderException(
                f"Failed to resolve RefPlaceholder: '{self.path}'"
            ) from exc


@dataclass
class GlobalRefPlaceholder(RefPlaceholder):
    """Reference Placeholder: '{global: <path>[, <default>]}'

    ref and global are identical, except that the map they resolve
    against is different.
    """

    # The order of the arguments is: all the attributes from the parent(s)
    # class(es) first then those of the child class.
    root_cfg: Optional[ConfigFn] = field(default=None, repr=False)

    def resolve(self, model: "ResolverMixin", memo: list):
        global_root = model.get_global_root()
        path = model.path_obj(self.path)
        return self._resolve_inner(global_root, path, memo)


class EnvvarConfigException(ConfigException):
    """EnvPlaceholder related exception"""


@dataclass
class EnvPlaceholder(Placeholder):
    """Environment Variable Placeholder: '{env: <env-var>[, <default>]}'"""

    env_var: str
    default_val: Any = DEFAULT

    def __post_init__(self):
        assert self.env_var

    def resolve(self, model: "ResolverMixin", memo: list):
        value = os.environ.get(self.env_var, self.default_val)
        if value is DEFAULT:
            raise EnvvarConfigException(
                f"Environment does not exist: '{self.env_var}'",
                # trace=new_trace(ctx=ctx, placeholder=self),
            )

        return value


@dataclass
class TimestampPlaceholder(Placeholder):
    """Replace yaml value with timestamp: '{timestamp: <format>}'"""

    format: str

    def __post_init__(self):
        assert self.format

    def resolve(self, model: "ResolverMixin", memo: list):
        now = datetime.now()
        value = now.strftime(self.format)
        return value

#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""Manage everything related to placeholders, such as
```
  db_engine: '{ref: db.engine, innodb}'
```

Placeholders can only occur in yaml values. They are not allowed in keys.
And it must be a yaml *string* value, surrounded by quotes.
"""

from abc import ABC, abstractmethod
import os
import logging
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional
from .config_getter import ConfigGetter


__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


class Placeholder(ABC):
    """A common base class for all Placeholders"""

    @abstractmethod
    def resolve(self, cfg, data: Mapping, *, _memo: list | None = None):
        """Resolve the placeholder"""


@dataclass
class ImportPlaceholder(Placeholder):
    """Import Placeholder: '{import: <file>[, <replace=False>]}'"""

    file: str | list

    def __post_init__(self):
        assert self.file
        if isinstance(self.file, (str, Path)):
            if Path(self.file).is_absolute():
                logger.warning("Absolut import file path detected: '%s'", self.file)

    def resolve(self, cfg, data: Mapping, *, _memo: list | None = None):
        file = cfg.resolve(self.file, data, _memo=_memo)
        rtn = cfg.load(file)
        return rtn


@dataclass
class RefPlaceholder(Placeholder):
    """Reference Placeholder: '{ref: <path>[, <default>]}'"""

    path: str
    default_val: Any = None
    file_root: Optional[Mapping] = None

    def __post_init__(self):
        assert self.path

    def resolve(self, cfg, data: Mapping, *, _memo: list | None = None):
        # Search order:
        #  1. CLI -> that is pretty clear  (where are the CLI data?)
        #  2. The env file
        #  3. The local file
        #  4. The main file
        # Maybe resolve should receive a list of Mappings?

        obj = self._resolve_inner(cfg, data)
        obj = cfg.resolve(obj, data, _memo=_memo)
        return obj

    def _resolve_inner(self, cfg, data: Mapping):
        try:
            obj = ConfigGetter().get(data, self.path)
            return obj
        except:  # pylint: disable=bare-except  # noqa: E722
            if self.default_val is not None:
                return obj

            raise


@dataclass
class GlobalRefPlaceholder(RefPlaceholder):
    """Reference Placeholder: '{global: <path>[, <default>]}'"""
    # TODO Not yet implemented. ref and global are identical, except
    # that the map they resolve against is different.


@dataclass
class EnvPlaceholder(Placeholder):
    """Environment Variable Placeholder: '{env: <env-var>[, <default>]}'"""

    env_var: str
    default_val: Any = None

    def __post_init__(self):
        assert self.env_var

    def resolve(self, *_, **__) -> str:
        value = os.environ.get(self.env_var, self.default_val)
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

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
from typing import Any, Mapping, Optional
from .config_getter import ConfigGetter


__parent__name__ = __name__.rpartition('.')[0]
logger = logging.getLogger(__parent__name__)


class Placeholder(ABC):
    """A common base class for all Placeholders
    """

    def post_load(self, _data: Mapping) -> None:
        """A hook that gets invoked after the yaml file has been loaded.

        E.g. to attach the file root dict with a Placeholder.

        :param _data: The dict associated with the file
        """

    @abstractmethod
    def resolve(self, data: Mapping):
        """Resolve the placeholder"""


@dataclass
class ImportPlaceholder(Placeholder):
    """Import Placeholder: '{import: <file>[, <replace=False>]}'
    """

    file: str

    def __post_init__(self):
        assert self.file

    def resolve(self, data: Mapping):
        pass     # Nothing to do


@dataclass
class RefPlaceholder(Placeholder):
    """Reference Placeholder: '{ref: <path>[, <default>]}'
    """

    path: str
    default_val: Any = None
    file_root: Optional[Mapping] = None

    def __post_init__(self):
        assert self.path

    def post_load(self, _data: Mapping) -> None:
        self.file_root = _data

    def resolve(self, data: Mapping):
        # 1. Search in the yaml file which contains the reference
        if self.file_root:
            try:
                obj = ConfigGetter.get(self.file_root, self.path, sep = ",")
                return obj.value
            except:     # pylint: disable=bare-except
                pass

        # 2. Search starting from the root of all the config files.
        obj = ConfigGetter.get(data, self.path, sep = ",", default = self.default_val)
        return obj.value


@dataclass
class EnvPlaceholder(Placeholder):
    """Environment Variable Placeholder: '{env: <env-var>[, <default>]}'
    """

    env_var: str
    default_val: Any = None

    def __post_init__(self):
        assert self.env_var

    def resolve(self, _) -> str:
        value = os.environ.get(self.env_var, self.default_val)
        return value


@dataclass
class TimestampPlaceholder(Placeholder):
    """Replace yaml value with timestamp: '{timestamp: <format>}'
    """

    format: str

    def __post_init__(self):
        assert self.format

    def resolve(self, _) -> str:
        now = datetime.now()
        value = now.strftime(self.format)
        return value

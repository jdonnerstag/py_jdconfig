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

    def post_load(self, _data: Mapping) -> None:
        """A hook that gets invoked after the yaml file has been loaded.

        E.g. to attach the file root dict with a Placeholder.

        :param _data: The dict associated with the file
        """

    @abstractmethod
    def resolve(self, data_1: Mapping, data_2: Optional[Mapping] = None):
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

    def resolve(self, *_):
        pass  # Nothing to do


@dataclass
class RefPlaceholder(Placeholder):
    """Reference Placeholder: '{ref: <path>[, <default>]}'"""

    path: str
    default_val: Any = None
    file_root: Optional[Mapping] = None

    def __post_init__(self):
        assert self.path

    def post_load(self, _data: Mapping) -> None:
        self.file_root = _data

    def resolve(self, data_1: Mapping, data_2: Optional[Mapping] = None):
        # Search order:
        #  1. CLI -> that is pretty clear  (where are the CLI data?)
        #  2. The env file
        #  3. The local file
        #  4. The main file
        # Maybe resolve should receive a list of Mappings?

        # Search in the env file, if provided
        if data_2:  # env file (2)
            try:
                obj = ConfigGetter.get(data_2, self.path, sep=",")
                return obj.value
            except:  # pylint: disable=bare-except  # noqa: E722
                pass

        # Search in the yaml file which contains the reference
        if self.file_root:  # local file (3)
            try:
                obj = ConfigGetter.get(self.file_root, self.path, sep=",")
                return obj.value
            except:  # pylint: disable=bare-except  # noqa: E722
                pass

        # Search starting from the root of all the config files.
        # Main file (4)
        obj = ConfigGetter.get(data_1, self.path, sep=",", default=self.default_val)
        return obj.value


@dataclass
class EnvPlaceholder(Placeholder):
    """Environment Variable Placeholder: '{env: <env-var>[, <default>]}'"""

    env_var: str
    default_val: Any = None

    def __post_init__(self):
        assert self.env_var

    def resolve(self, *_) -> str:
        value = os.environ.get(self.env_var, self.default_val)
        return value


@dataclass
class TimestampPlaceholder(Placeholder):
    """Replace yaml value with timestamp: '{timestamp: <format>}'"""

    format: str

    def __post_init__(self):
        assert self.format

    def resolve(self, *_) -> str:
        now = datetime.now()
        value = now.strftime(self.format)
        return value

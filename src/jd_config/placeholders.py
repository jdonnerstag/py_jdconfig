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
import typing
from typing import Any, Callable, Mapping, Optional, Type

from .config_path import CfgPath
from .file_loader import ConfigFile
from .utils import DEFAULT, ConfigException, ContainerType, Trace

if typing.TYPE_CHECKING:
    from jd_config.resolvable_base_model import ResolvableBaseModel

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


def new_trace(ctx: "GetterContext", placeholder: "Placeholder" = None):
    """Create a new Trace or None"""

    if not ctx:
        return None

    filename = None
    if isinstance(ctx.current_file, ConfigFile):
        filename = ctx.current_file.file_1

    return Trace(path=ctx.cur_path(), placeholder=placeholder, file=filename)


class PlaceholderException(ConfigException):
    """Placeholder exception"""


# pylint: disable=too-few-public-methods
class Placeholder(ABC):
    """A common base class for all Placeholders"""

    @abstractmethod
    def resolve(self, model: "ResolvableBaseModel", expected_type: Type):
        """Resolve the placeholder"""


LoaderType = Callable[[str], Mapping]


@dataclass
class ImportPlaceholder(Placeholder):
    """Import Placeholder: '{import: <file>[, <replace=False>]}'"""

    file: str
    cache: bool = field(default=True, repr=False)

    cache_key: str = field(default=None, repr=False)
    cache_value: Any = field(default=None, repr=False)

    def __post_init__(self):
        assert self.file
        if isinstance(self.file, (str, Path)):
            if Path(self.file).is_absolute():
                logger.warning("Absolut import file path detected: '%s'", self.file)

    def resolve(self, model: "ResolvableBaseModel", expected_type: Type):
        assert model.__model_meta__.app
        app = model.__model_meta__.app
        assert app.load_import
        assert callable(app.load_import)

        file = model.resolve(self.file, str)
        file = Path(file)

        if self.cache_key == file:
            return self.cache_value

        rtn = app.load_import(file, cache=self.cache)
        value = model.load_item(rtn, expected_type)

        if self.cache:
            self.cache_key = file
            self.cache_value = value

        return value


@dataclass
class RefPlaceholder(Placeholder):
    """Reference Placeholder: '{ref: <path>[, <default>]}'"""

    path: str
    default_val: Any = None

    def __post_init__(self):
        assert self.path

    def resolve(self, model: "ResolvableBaseModel", expected_type: Type):
        path = CfgPath(self.path)
        if path and path[0] in [CfgPath.PARENT_DIR, CfgPath.CURRENT_DIR]:
            while path and path[0] in [CfgPath.PARENT_DIR, CfgPath.CURRENT_DIR]:
                if path[0] == CfgPath.PARENT_DIR:
                    model = model.__model_meta__.parent

                path = path[1:]
        else:
            model = model.__model_meta__.file.obj

        return self._resolve_inner(model, path)

    def _resolve_inner(self, model, path):
        try:
            obj = model
            for elem in path:
                obj = getattr(obj, elem)
            return obj
        except (
            KeyError,
            IndexError,
        ) as exc:  # pylint: disable=bare-except  # noqa: E722
            if self.default_val is not None:
                return obj

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

    def resolve(self, model: "ResolvableBaseModel", expected_type: Type):
        path = CfgPath(self.path)
        model = model.__model_meta__.root.obj

        return self._resolve_inner(model, path)


class EnvvarConfigException(ConfigException):
    """EnvPlaceholder related exception"""


@dataclass
class EnvPlaceholder(Placeholder):
    """Environment Variable Placeholder: '{env: <env-var>[, <default>]}'"""

    env_var: str
    default_val: Any = DEFAULT

    def __post_init__(self):
        assert self.env_var

    def resolve(self, model: "ResolvableBaseModel", expected_type: Type):
        value = os.environ.get(self.env_var, self.default_val)
        if value is DEFAULT:
            raise EnvvarConfigException(f"ENV var does not exist: '{self.env_var}'")

        return value


@dataclass
class TimestampPlaceholder(Placeholder):
    """Replace yaml value with timestamp: '{timestamp: <format>}'"""

    format: str

    def __post_init__(self):
        assert self.format

    def resolve(self, model: "ResolvableBaseModel", expected_type: Type):
        now = datetime.now()
        value = now.strftime(self.format)
        return value

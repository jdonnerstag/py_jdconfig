#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
A python package to load and maintain and application's configurations.

Please see the readme.md file for details. In summary:
1. Yaml based configuration files
1. Environment (dev, test, prod) specific configurations adjusting default values,
   and not interfering with each other. Can all be committed into git.
1. For more structure, configs can be split into multiple files
1. A config directory can be configured, to keep config files separate from
   source code or documentation.
1. Yaml string values support placeholders, like '..{<name>: <val>, ...}..'
1. Import config files: '{import: <file>}'
1. Reference another value: 'Hello {ref: <path>[, <default>]}'
1. A yaml value that is '???' is mandotory and must be provided via env overlay
   or CLI args.
"""

from .config_ini_mixin import ConfigIniMixin
from .config_path import CfgPath, PathType
from .config_path_extended import ExtendedCfgPath
from .file_loader import ConfigFile, ConfigFileLoader, ConfigFileLoggerMixin
from .jd_config import JDConfig
from .placeholders import (
    EnvPlaceholder,
    GlobalRefPlaceholder,
    ImportPlaceholder,
    Placeholder,
    PlaceholderException,
    RefPlaceholder,
    TimestampPlaceholder,
    new_trace,
)
from .stats import ConfigStats
from .string_converter_mixin import StringConverterMixin
from .utils import (
    DEFAULT,
    ConfigException,
    ContainerType,
    NonStrSequence,
    Trace,
    relative_to_cwd,
)
from .value_reader import RegistryType, ValueReader, ValueReaderException, ValueType

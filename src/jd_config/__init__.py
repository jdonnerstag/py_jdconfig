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

from .utils import NonStrSequence, ConfigException, PathType
from .config_ini_mixin import ConfigIniMixin
from .string_converter_mixin import StringConverterMixin

from .objwalk import (
    ObjectWalker,
    NodeEvent,
    NewMappingEvent,
    NewSequenceEvent,
    DropContainerEvent,
    WalkerEvent,
)

from .config_path import ConfigPath
from .config_getter import ConfigGetter
from .placeholders import (
    PlaceholderException,
    Placeholder,
    ImportPlaceholder,
    RefPlaceholder,
    GlobalRefPlaceholder,
    EnvPlaceholder,
    TimestampPlaceholder,
)

from .value_reader import ValueType, ValueReader
from .deep_getter_with_search import ConfigSearchPlugin
from .deep_getter_with_search_and_resolver import ConfigResolvePlugin
from .deep_access_mixin import DeepAccessMixin
from .deep_dict import DeepDict
from .config_file_loader import ConfigFileLoader
from .deep_export_mixin import DeepExportMixin
from .deep_update import DeepUpdateMixin
from .jd_config import JDConfig

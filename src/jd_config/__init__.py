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

from .config_file_loader import ConfigFileLoader
from .config_getter import ConfigGetter
from .config_ini_mixin import ConfigIniMixin
from .config_path import ConfigPath
from .deep_access_mixin import DeepAccessMixin
from .deep_dict import DeepDict
from .deep_export_mixin import DeepExportMixin
from .deep_getter_with_search import ConfigSearchMixin
from .deep_getter_with_search_and_resolver import ConfigResolveMixin
from .deep_update import DeepUpdateMixin
from .jd_config import JDConfig
from .objwalk import (
    DropContainerEvent,
    NewMappingEvent,
    NewSequenceEvent,
    NodeEvent,
    ObjectWalker,
    WalkerEvent,
)
from .placeholders import (
    EnvPlaceholder,
    GlobalRefPlaceholder,
    ImportPlaceholder,
    Placeholder,
    PlaceholderException,
    RefPlaceholder,
    TimestampPlaceholder,
)
from .string_converter_mixin import StringConverterMixin
from .utils import ConfigException, NonStrSequence, PathType
from .value_reader import ValueReader, ValueType

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

from .string_converter_mixin import StringConverterMixin

from .objwalk import (
    objwalk,
    NodeEvent,
    NewMappingEvent,
    NewSequenceEvent,
    DropContainerEvent,
    WalkerEvent,
)

from .extended_yaml_file_loader import (
    YamlObj,
    YamlContainer,
    YamlMapping,
    YamlSequence,
    MyYamlSafeLoader,
)

from .config_getter import ConfigException, ConfigGetter

from .placeholders import (
    Placeholder,
    ImportPlaceholder,
    RefPlaceholder,
    EnvPlaceholder,
    TimestampPlaceholder,
)

from .value_reader import ValueType, ValueReaderException, ValueReader

from .deep_access_mixin import DeepAccessMixin
from .config_file_loader import ConfigFileLoader
from .deep_export_mixin import DeepExportMixin
from .resolver_mixin import ResolverMixin
from .jd_config import JDConfig

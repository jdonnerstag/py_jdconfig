#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
A python package to load and maintain and application's configurations.

Please see the readme.md file for details. In summary:
1. Yaml based configuration files
1. Environment (dev, test, prod) specific configurations adjusting default values,
   and not interfering with each other. Can all be committed into git.
1. For more structure, configs can be split into multiple file
1. A config directory can be configured, to keep config files separate
1. A Yaml !import tag can be used to eagerly load another yaml config file.
1. Yaml string values support extendable placeholders, like '..{<name>: <val>, ...}..'
1. Import config file: '{import: <file>[, <env> [, <replace>]]}'
1. Reference: '{ref: <path>[, <default>]}'
1. A yaml value that is '???' is mandotory and must be provided via env overlay or CLI args.
"""

from .objwalk import (
    objwalk
)

from .yaml_loader import (
    YamlObj,
    YamlContainer,
    YamlMapping,
    YamlSequence,
    MyYamlLoader
)

from .config_getter import (
    ConfigException,
    ConfigGetter
)

from .placeholder import (
    CompoundValue,
    ValueType,
    Placeholder,
    ImportPlaceholder,
    RefPlaceholder,
    ValueReaderException,
    ValueReader,
    convert_bool
)

from .jd_config import (
    JDConfig
)

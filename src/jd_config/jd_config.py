#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Main config package to load and access config values.
"""

from io import StringIO
import logging
import os
from pathlib import Path
from typing import Mapping, Optional
from .config_ini_mixin import ConfigIniMixin
from .deep_access_mixin import DeepAccessMixin
from .config_file_loader import ConfigFileLoader
from .deep_export_mixin import DeepExportMixin
from .resolver_mixin import ResolverMixin

__parent__name__ = __name__.rpartition('.')[0]
logger = logging.getLogger(__parent__name__)


class JDConfig(
    ConfigIniMixin,
    ResolverMixin,
    DeepAccessMixin,
    DeepExportMixin,
):
    """Main class load and access config values.
    """

    def __init__(self, *, ini_file: str = "config.ini") -> None:
        """Initialize.

        User and Config specific configurations are kept separate.
        'JDConfig' can be configured by means of 'config.ini'

        Only the '[config]' section will be used. Everything else will
        be ignored. The following keys (and default values) are supported.

        ```
        [config]
        config_dir = .
        config_file = config.yaml
        env_var =
        default_env = prod
        ```

        Some of the JDConfig configs determine where to find the user
        specific configurations files, including environment specific
        overlays.

        :param ini_file: Path to JDConfig config file. Default: 'config.ini'
        """

        # The yaml config data after loading them
        self.data = None

        ConfigIniMixin.__init__(self, ini_file=ini_file)

        ResolverMixin.__init__(self)

        DeepAccessMixin.__init__(self)

        ConfigFileLoader.__init__(self)

        DeepExportMixin.__init__(self)

        # Why this approach and not a Mixin/Base Class. ConfigFileLoader
        # is comparatively large with a number of functions. Functions
        # which I consider private, but python has not means to mark them
        # private. This is a more explicit approach.
        self.config_file_loader = ConfigFileLoader(dependencies=self)

    @property
    def files_loaded(self):
        return self.config_file_loader.files_loaded

    @property
    def file_recursions(self):
        return self.config_file_loader.file_recursions


    def load(self, fname: Path|StringIO, config_dir: Path, env: str|None = None) -> Mapping:

        fname = fname or self.config_file
        config_dir = config_dir or self.config_dir
        env = env or self.env

        # Make the yaml config data accessible via JDConfig
        self.data = self.config_file_loader.load(fname, config_dir, env)
        return self.data

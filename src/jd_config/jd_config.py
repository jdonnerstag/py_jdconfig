#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Main config package to load and access config values.
"""

import logging
from .config_ini_mixin import ConfigIniMixin
from .deep_access_mixin import DeepAccessMixin
from .config_loader_mixin import YamlFileLoaderMixin
from .deep_export_mixin import DeepExportMixin
from .resolver_mixin import ResolverMixin

__parent__name__ = __name__.rpartition('.')[0]
logger = logging.getLogger(__parent__name__)


class JDConfig(
    ConfigIniMixin,
    YamlFileLoaderMixin,
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

        YamlFileLoaderMixin.__init__(self)

        DeepExportMixin.__init__(self)

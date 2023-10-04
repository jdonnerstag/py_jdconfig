#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Main config package to load and access config values.
"""

from io import StringIO
import logging
from pathlib import Path
from typing import Mapping, Optional, Sequence, Union
from .config_ini_mixin import ConfigIniMixin
from .deep_access_mixin import DeepAccessMixin
from .config_file_loader import ConfigFileLoader
from .deep_export_mixin import DeepExportMixin
from .resolver_mixin import ResolverMixin

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


class JDConfig(ConfigIniMixin, ResolverMixin, DeepAccessMixin, DeepExportMixin):
    """Main class load and access config values."""

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

        DeepExportMixin.__init__(self)

        # Why this approach and not a Mixin/Base Class. ConfigFileLoader
        # is comparatively large with a number of functions. Functions
        # which I consider private, but python has not means to mark them
        # private. This is a more explicit approach.
        self.config_file_loader = ConfigFileLoader()

    def load(
        self,
        fname: Optional[Path | StringIO] = None,
        config_dir: Optional[Path] = None,
        env: str | None = None,
    ) -> Mapping:
        """Main entry point to load configs"

        The filename can be relativ or absolute. If relativ, it will loaded
        relativ to 'config_dir'

        Alternatively 'fname' can be an file descriptor, e.g. 'fd = io.StringIO("...")'
        or 'with open("myfile.yaml", "rb") as fd:'.

        'config_dir' is especially relevant when importing additional config files,
        e.g. 'db: {import: ./db/database-config.yaml}

        :param fname: yaml config file (optional)
        :param config_dir: working directory for loading config files (optional)
        :param env: environment name (optional)
        """

        if fname is None:
            fname = self.config_file

        if isinstance(fname, str):
            fname = Path(fname)

        config_dir = Path(config_dir or self.config_dir)
        env = env or self.env

        # Make the yaml config data accessible via JDConfig
        data = self.config_file_loader.load(fname, config_dir, env)
        if self.data is None:
            self.data = data
        return data

    def on_missing_handler(
        self,
        data: Mapping | Sequence,
        key: str | int,
        path: tuple,
        create_missing: Union[callable, bool, Mapping],
    ) -> Mapping | Sequence:
        """A handler that will be invoked if a path element is missing and
        'create_missing has valid configuration.
        """

        if key in data:
            value = data[key]
            if isinstance(value, str) and value.find("{") != -1:
                value = self.resolve(value, self.data)
                return value

        # From DeepAccessMixin. Not easy to know ?!? Need something simple / more obvious
        return self._cfg_getter.on_missing_handler(data, key, path, create_missing)

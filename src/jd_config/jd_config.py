#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Main config module to load and access config values.
"""

import logging
from io import StringIO
from pathlib import Path
from typing import Any, Mapping, Optional

from jd_config.config_base_model import ConfigBaseModel, ConfigMeta


from .resolvable_base_model import ResolvableBaseModel
from .config_ini_mixin import ConfigIniMixin
from .config_path import PathType, CfgPath
from .file_loader import ConfigFile
from .utils import ContainerType
from .value_reader import RegistryType, ValueReader
from .provider_registry import ProviderRegistry

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


class JDConfig(ConfigIniMixin):
    """Main class load and access config values."""

    def __init__(
        self, model_type: ResolvableBaseModel, *, ini_file: str = "config.ini"
    ) -> None:
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
        ConfigIniMixin.__init__(self, ini_file=ini_file)

        # Providers are plugins, which can easily be added. By default,
        # only a yaml config file loader is available. Additional ones,
        # may leverage VFS, etcd, git, web-servers, AWS parameter stores, etc..
        self.provider_registry = ProviderRegistry(self)

        # We want access to the placeholder registry which is maintained by ValueReader.
        self.value_reader = ValueReader()

        # The global config root object
        self.model_type = model_type
        self.data: Optional[ResolvableBaseModel] = None

        # Files loaded by the yaml file loader
        self.files_loaded: list[str | Path] = []

    def config(self) -> ResolvableBaseModel:
        """Get the config object"""
        return self.data

    @property
    def config_dir(self) -> str | None:
        """Default working directory to load/import files"""
        return self.ini.config_dir

    @property
    def config_file(self) -> str | None:
        """The main config file"""
        return self.ini.config_file

    @property
    def env(self) -> str | None:
        """The config environment, such as dev, test, prod"""
        return self.ini.env

    @property
    def placeholder_registry(self) -> RegistryType:
        """The registry of supported Placeholder handlers"""
        return self.value_reader.registry

    def validate(self, path: Optional[PathType] = None) -> dict:
        """Validate the configuration by accessing and resolving all values,
        all file imports, all environment files, etc..

        It validates the config data currently loaded. To validate another
        combination (e.g. another dev, test environment overlay), re-load
        the data.
        """

        return self.data.to_dict(path)

    def load_import(
        self,
        fname: Path | StringIO,
        config_dir: Optional[Path] = None,
        env: str | None = None,
        cache: bool = True,
    ) -> ConfigFile:
        """Used by {import:} to laod a config file

        See load() for more details

        :param fname: yaml config file (optional)
        :param config_dir: overwrite self.config_dir to load the file. Default is to
        use self.config_dir (see config.ini)
        :param env: environment name (optional)
        """

        data = self.provider_registry.load(
            fname,
            config_dir=config_dir,
            env=env,
            cache=cache,
            add_env_dirs=self.ini.add_env_dirs,
        )

        return data

    def load(
        self,
        fname: Optional[Path | StringIO] = None,
        config_dir: Optional[Path] = None,
        env: str | None = None,
        cache: bool = True,
    ) -> ConfigBaseModel:
        """Main entry point to load configs"

        The filename can be relativ or absolute. If relativ, it will be loaded
        relativ to 'config_dir'

        Alternatively 'fname' can be a file descriptor, e.g. 'fd = io.StringIO("...")'
        or 'with open("myfile.yaml", "rb") as fd:'.

        :param fname: yaml config file (optional)
        :param config_dir: overwrite self.config_dir to load the file. Default is to
        use self.config_dir (see config.ini)
        :param env: environment name (optional)
        """

        if fname is None:
            fname = self.ini.config_file

        file = self.load_import(fname, config_dir, env, cache)

        meta = ConfigMeta(app=self, data=file)
        self.data = self.model_type(meta=meta)

        return self.data

    def get(self, path: PathType) -> Any:
        path = CfgPath(path)
        rtn = self.data
        for elem in path:
            if isinstance(elem, Mapping):
                rtn = rtn[elem]
            else:
                rtn = getattr(rtn, elem)

        return rtn

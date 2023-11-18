#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Providers are plugins, which can easily be added. By default,
only a yaml config file loaded is available. Additional ones,
may leverage VFS, etcd, git, web-servers, AWS parameter stores, etc..
"""

import logging
from abc import ABC, abstractmethod
from io import StringIO
from os import PathLike
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from .file_loader import ConfigFileLoader

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


class ProviderPlugin(ABC):
    """Abstract base class for config providers"""

    name: str  # An abstract variable

    def __init__(self, app: Any = None) -> None:
        # Plugins often require additional info, which an 'app' like
        # object could provde. E.g. the default yaml file plugin requires
        # 'config_dir', 'env' and 'cache'
        self.app = app

    @abstractmethod
    def load(self, name: Optional[Path | StringIO], **kvargs) -> Mapping | None:
        """Load and return the data, or return None to indicate that the
        provider does not know how to handle this URL/file
        """
        return {}


class YamlFileProviderPlugin(ProviderPlugin):
    """The default yaml file and bytes loader"""

    name: str = "Yaml files"

    def __init__(self, app: Any = None) -> None:
        super().__init__(app)

        self.loader = ConfigFileLoader()

    def load(
        self,
        name: Optional[Path | StringIO],
        config_dir: Optional[PathLike | Sequence[PathLike]] = None,
        env: Optional[str] = None,
        **kvargs,
    ) -> Mapping | None:
        """Load and return the data, or return None to indicate that the
        provider does not know how to handle this URL/file
        """

        fname = self.app.ini.config_file if name is None else name
        config_dir = self.app.ini.config_dir if config_dir is None else config_dir
        env = self.app.ini.env if env is None else env

        # Might as well be a StreamIO.
        if isinstance(fname, str):
            fname = Path(fname)

        file = self.loader.load(fname, config_dir, env)

        if hasattr(self.app, "files_loaded"):
            self.app.files_loaded = self.loader.files_loaded

        return file


class ProviderRegistry:
    """Providers are plugins, which can easily be added. By default,
    only a yaml config file loaded is available. Additional ones,
    may leverage VFS, etcd, git, web-servers, AWS parameter stores, etc..
    """

    def __init__(self, app=None) -> None:
        self.registry: list[ProviderPlugin] = [YamlFileProviderPlugin(app)]

    def append(self, plugin: ProviderPlugin):
        """Append a provider"""
        self.registry.append(plugin)

    def insert(self, idx: int, plugin: ProviderPlugin):
        """Insert a provider at the position provided"""
        self.registry.insert(idx, plugin)

    def provider_names(self):
        """Every provider has a 'name'. Get a list with names of all
        registered providers
        """
        names = [plugin.name for plugin in self.registry]
        return names

    def load(self, fname: Optional[Path | StringIO], **kvargs) -> Mapping:
        """Iterate over all providers and try to load the config data.

        Return the data from the first provider that succeeded.
        """

        for plugin in self.registry:
            try:
                rtn = plugin.load(fname, **kvargs)
                if rtn is not None:
                    return rtn
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logger.warning(str(exc))

        raise FileNotFoundError(
            f"None of the config providers was able to load: '{fname}'. "
            f"Registered providers: {self.provider_names()}"
        )

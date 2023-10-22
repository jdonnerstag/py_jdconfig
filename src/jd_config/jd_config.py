#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Main config module to load and access config values.
"""

import logging
from functools import partial
from io import StringIO
from pathlib import Path
from typing import Any, Iterator, Optional

from .config_ini_mixin import ConfigIniMixin
from .deep_dict import DeepDict, DefaultConfigGetter
from .deep_getter import GetterContext
from .file_loader import ConfigFile, ConfigFileLoader
from .objwalk import WalkerEvent
from .utils import DEFAULT, ContainerType, PathType
from .value_reader import RegistryType, ValueReader

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


class JDConfig(ConfigIniMixin):
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
        ConfigIniMixin.__init__(self, ini_file=ini_file)

        # Utils to load the config file(s)
        self.config_file_loader = ConfigFileLoader()

        # We want access to the placeholder registry which is maintained by ValueReader.
        self.value_reader = ValueReader()

        # We want the same Getter with the same configuration everywhere
        self.getter = DefaultConfigGetter(value_reader=self.value_reader)

        # The ImportPlaceholder need to know how to load files
        orig_import_placeholder = self.value_reader.registry["import"]
        self.value_reader.registry["import"] = partial(
            orig_import_placeholder, loader=self
        )

        # The GlobalRefPlaceholder needs to know the global config
        orig_global_placeholder = self.value_reader.registry["global"]
        self.value_reader.registry["global"] = partial(
            orig_global_placeholder, root_cfg=self.config
        )

        # The global config root object
        self.data = None

    def config(self) -> ContainerType:
        """Get the config object"""
        return self.data

    @property
    def config_dir(self) -> str | None:
        """Default working directory to load/import files"""
        return self.ini["config_dir"]

    @property
    def config_file(self) -> str | None:
        """The main config file"""
        return self.ini["config_file"]

    @property
    def env(self) -> str | None:
        """The config environment, such as dev, test, prod"""
        return self.ini["env"]

    @property
    def placeholder_registry(self) -> RegistryType:
        """The registry of supported Placeholder handlers"""
        return self.value_reader.registry

    @property
    def files_loaded(self) -> list[Path]:
        """The list of files loaded so far"""
        return self.config_file_loader.files_loaded

    def get(self, path: PathType, default: Any = DEFAULT, resolve: bool = True) -> Any:
        """Get a config value (or node)"""
        return self.data.get(path, default=default, resolve=resolve)

    def walk(
        self,
        path: PathType = (),
        *,
        nodes_only: bool = False,
        resolve: bool = True,
        ctx: Optional[GetterContext] = None
    ) -> Iterator[WalkerEvent]:
        """Walk a subtree, with lazily resolving node values"""

        path = self.getter.normalize_path(path)
        root = self.get(path, resolve=True)
        ctx = self.getter.new_context(
            data=root, files=[self.data], skip_resolver=not resolve
        )

        yield from self.getter.walk_tree(ctx, nodes_only=nodes_only)

    def to_dict(self, path: Optional[PathType] = None, resolve: bool = True) -> dict:
        """Walk the config items with an optional starting point, and create a
        dict from it.
        """

        return self.getter.to_dict(self.data, path, resolve=resolve)

    def to_yaml(self, path: Optional[PathType] = None, stream=None, **kvargs):
        """Convert the configs (or part of it), into a yaml document"""

        return self.getter.to_yaml(self.data, path, stream=stream, **kvargs)

    def validate(self, path: Optional[PathType] = None) -> dict:
        """Validate the configuration by accessing and resolving all value,
        all file imports, all environment files, etc.."""

        # TODO add env name, to validate a specifc env setup
        return self.to_dict(path, resolve=True)

    def resolve_all(self, path: Optional[PathType] = None) -> DeepDict:
        """Resolve configs in memory and replace in memory the current one.

        Different to 'to_dict()' which creates a copy of the tree and returns
        it, 'resolve_all()' will modify the config. Though, in memory only.
        The files are never modified.

        :param path: Only resolve config within the subtree
        """

        logger.debug("Resolve all config placeholders for '%s'", path)
        data = self.getter.to_dict(self.data, path, resolve=True)

        if not path:
            if not isinstance(data, DeepDict) and isinstance(data, ContainerType):
                data = DeepDict(data, getter=self.getter)

            self.data = data
        else:
            self.data.set(path, data)

        return data

    def load(
        self,
        fname: Optional[Path | StringIO] = None,
        config_dir: Optional[Path] = None,
        env: str | None = None,
        cache: bool = True,
    ) -> ConfigFile:
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
            fname = self.config_file

        if isinstance(fname, str):
            fname = Path(fname)

        config_dir = Path(config_dir or self.config_dir)
        env = env or self.env

        # Load the file
        file = self.config_file_loader.load(fname, config_dir, env, cache)

        # Make the yaml config data accessible via JDConfig
        if self.data is None and isinstance(file, ContainerType):
            self.data = DeepDict(file, getter=self.getter)

            if self.ini["resolve_eagerly"]:
                self.data = self.resolve_all()

            return self.data

        return file

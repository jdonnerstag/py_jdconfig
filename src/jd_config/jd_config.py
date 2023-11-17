#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Main config module to load and access config values.
"""

import logging
from functools import partial
from io import StringIO
from pathlib import Path
from typing import Any, Iterator, Optional, Type

from pydantic import BaseModel

from .config_ini import ConfigIni
from .config_path import CfgPath, PathType
from .deep_dict_mixin import DeepDictMixin
from .deep_search_mixin import DeepSearchMixin
from .file_loader import ConfigFile
from .getter_context import GetterContext
from .objwalk import WalkerEvent
from .provider_registry import ProviderRegistry
from .utils import DEFAULT, ConfigException, ContainerType
from .value_reader import RegistryType, ValueReader

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


class JDConfig:
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
        self.ini, self.ini_file = ConfigIni().load(ini_file, "config")

        # Providers are plugins, which can easily be added. By default,
        # only a yaml config file loader is available. Additional ones,
        # may leverage VFS, etcd, git, web-servers, AWS parameter stores, etc..
        self.provider_registry = ProviderRegistry(self)

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

        # Files loaded by the yaml file loader
        self.files_loaded: list[str | Path] = []

    def config(self) -> ContainerType:
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

    def get_into(self, path: PathType, into: Optional[Type]) -> Any:
        """Get a config value (or node)

        In case path requires a special separator, use e.g.
        'CfgPath(path, sep="/")' to create the path.
        """

        if isinstance(into, type):
            if not issubclass(into, BaseModel):
                raise ConfigException(
                    f"Expected a class subclassed from pydantic.BaseModel: '{into.__name__}'"
                )
        else:
            raise ConfigException(
                f"Expected a class, not an instance of a class: '{into}'"
            )

        rtn = self.data.get(path, resolve=True)
        rtn = into(**rtn)
        return rtn

    def get(self, path: PathType, default: Any = DEFAULT, resolve: bool = True) -> Any:
        """Get a config value (or node)

        In case path requires a special separator, use e.g.
        'CfgPath(path, sep="/")' to create the path.
        """
        rtn = self.data.get(path, default=default, resolve=resolve)
        return rtn

    def walk(
        self,
        path: PathType = (),
        *,
        nodes_only: bool = False,
        resolve: bool = True,
        ctx: Optional[GetterContext] = None,
    ) -> Iterator[WalkerEvent]:
        """Walk a subtree, with lazily resolving node values"""

        path = CfgPath(path)
        root = self.get(path, resolve=True)
        ctx = self.getter.new_context(
            data=root, current_file=self.data, skip_resolver=not resolve
        )

        yield from DeepSearchMixin.walk_tree(ctx, nodes_only=nodes_only)

    def to_dict(self, path: Optional[PathType] = None, resolve: bool = True) -> dict:
        """Walk the config items with an optional starting point, and create a
        dict from it.
        """

        return self.getter.to_dict(self.data, path, resolve=resolve)

    def to_yaml(self, path: Optional[PathType] = None, stream=None, **kvargs):
        """Convert the configs (or part of it), into a yaml document"""

        return self.getter.to_yaml(self.data, path, stream=stream, **kvargs)

    def validate(self, path: Optional[PathType] = None) -> dict:
        """Validate the configuration by accessing and resolving all values,
        all file imports, all environment files, etc..

        It validates the config data currently loaded. To validate another
        combination (e.g. another dev, test environment overlay), re-load
        the data.
        """

        return self.to_dict(path, resolve=True)

    def resolve_all(self, path: Optional[PathType] = None) -> DeepDictMixin:
        """Resolve configs in memory and replace in memory the current one.

        Different to 'to_dict()' which creates a copy of the tree and returns
        it, 'resolve_all()' will modify the config. Though, in memory only.
        The files are never modified.

        :param path: Only resolve config within the subtree
        """

        path = CfgPath(path)
        logger.debug("Resolve all config placeholders for '%s'", path)
        data = self.getter.to_dict(self.data, path, resolve=True)

        if not path:
            if not isinstance(data, DeepDictMixin) and isinstance(data, ContainerType):
                data = DeepDictMixin(data, getter=self.getter)

            self.data = data
        else:
            self.data.set(path, data)

        return data

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
            add_env_dirs=self.ini.env_dirs,
        )

        return data

    def load(
        self,
        fname: Optional[Path | StringIO] = None,
        config_dir: Optional[Path] = None,
        env: str | None = None,
        cache: bool = True,
    ) -> DeepDictMixin:
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

        self.data = DeepDictMixin(file, getter=self.getter)

        return self.data

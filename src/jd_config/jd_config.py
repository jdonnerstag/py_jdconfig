#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Main config package to load and access config values.
"""

import os
import logging
import configparser
from typing import Any,  Mapping, Optional
from .placeholder import ImportPlaceholder, RefPlaceholder, ValueReader
from .placeholder import CompoundValue
from .objwalk import objwalk
from .config_getter import ConfigGetter, ConfigException
from .yaml_loader import YamlObj, MyYamlLoader

__parent__name__ = __name__.rpartition('.')[0]
logger = logging.getLogger(__parent__name__)


class JDConfig:
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

        config = configparser.ConfigParser()
        if ini_file:
            logger.debug("Config: Load ini-file: '%s'", ini_file)
            config.read(ini_file)

        try:
            config = config["config"]
        except KeyError:
            config = {}

        self.config_dir = config.get("config_dir", ".")
        self.config_file = config.get("config_file", "config.yaml")
        self.env_var = config.get("env_var", None)
        self.default_env = config.get("default_env", "prod")


    def load_yaml_raw(self, fname: os.PathLike) -> Mapping:
        """Load a Yaml file with our Loader, but no post-processing

        :param fname: the yaml file to load
        :return: A deep dict-like structure, representing the yaml content
        """

        # pyyaml will consider the BOM, if available,
        # and decode the bytes. utf-8 is default.
        logger.debug("Config: Load from file: '%s'", fname)
        with open(fname, "rb") as fd:
            loader = MyYamlLoader(fd)
            return loader.get_single_data()


    def load(self,
        fname: Optional[os.PathLike] = None,
        config_dir: Optional[os.PathLike] = None
    ) -> Mapping:
        """Load a Yaml config file, determine and load 'imports', and
        pre-process for efficient, yet lazy, key/value resolution.

        :param fname: the yaml file to load. Default: config file configured in config.ini
        """

        if fname is None:
            fname = self.config_file

        if config_dir is None:
            config_dir = self.config_dir

        if not os.path.isabs(fname):
            fname = os.path.join(config_dir, fname)

        _data = self.load_yaml_raw(fname)

        _data = self.process_imports(_data, config_dir)

        return _data

    def process_imports(self, _data: Mapping, config_dir: os.PathLike) -> Mapping:
        """Search for import placeholder and execute them

        :param _data: the yaml data loaded already
        :return: the updated yaml data with imports replaced.
        """

        imports: dict[Any, ImportPlaceholder] = {}
        for path, obj in objwalk(_data):
            value = obj.value
            if isinstance(value, str) and value.find("{") != -1:
                value = obj.value = CompoundValue(ValueReader().parse(value))
                if value.is_import():
                    imports[path] = value[0]

        for path, obj in imports.items():
            fname = self.resolve(obj.file, _data)
            import_data = self.load(fname, config_dir)
            if obj.replace:
                ConfigGetter.delete(_data, path)
                _data.update(import_data)
            else:
                ConfigGetter.set(_data, path, import_data)

        return _data

    def resolve(self, value: Any, _data: Optional[Mapping] = None):
        """Lazily resolve Placeholders

        Yaml values may contain our Placeholder. Upon loading a yaml file,
        a CompoundValue will be created, for every yaml value that contains
        a Placeholder. resolve() lazily resolves the placeholders and joins
        the pieces together for the actuall yaml value.
        """

        if isinstance(value, RefPlaceholder):
            value = ConfigGetter.get(_data, value.path, sep = ",", default = value.default)
            if isinstance(value, YamlObj):
                value = value.value

        if isinstance(value, list):
            value = [self.resolve(x, _data) for x in value]
            value = "".join(value)
            return value

        if isinstance(value, (str, int, float, bool)):
            return value

        raise ConfigException(f"Unable to resolve: '${value}'")

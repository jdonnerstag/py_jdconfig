#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import os
import logging
from typing import Any, Iterator, Mapping, Optional
import configparser
from .placeholder import ImportPlaceholder, RefPlaceholder, ValueReader
from .placeholder import ValueType, ValueReaderException
from .objwalk import objwalk
from .config_getter import ConfigGetter
from .jd_yaml_loader import YamlObj, MyYamlLoader

logger = logging.getLogger(__name__)


class ConfigException(Exception):
    pass

class CompoundValue(list):

    def __init__(self, values: Iterator['ValueType']) -> None:
        super().__init__(list(values))

    def is_import(self) -> bool:
        for elem in self:
            if isinstance(elem, ImportPlaceholder):
                if len(self) != 1:
                    raise ValueReaderException("Invalid '{import: ...}', ${elem}")

                return True

        return False


class JDConfig:

    def __init__(self, ini_file: str = "config.ini") -> None:
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
        self.env_key = config.get("env_key", None)
        self.default_env = config.get("default_env", "prod")

    def load_yaml_raw(self, fname: os.PathLike) -> Mapping:
        # pyyaml will consider the BOM, if available,
        # and decode the bytes. utf-8 is default.
        logger.debug("Config: Load from file: '%s'", fname)
        with open(fname, "rb") as fd:
            loader = MyYamlLoader(fd)
            return loader.get_single_data()

    def load(self, fname: Optional[os.PathLike]) -> Mapping:
        if fname is None:
            fname = self.config_dir + "/" + self.config_file
        else:
            if not os.path.isabs(fname):
                fname = self.config_dir + "/" + fname

        _data = self.load_yaml_raw(fname)

        imports: dict[Any, ImportPlaceholder] = {}
        for path, obj in objwalk(_data):
            value = obj.value
            if isinstance(value, str) and value.find("{") != -1:
                value = obj.value = CompoundValue(ValueReader().parse(value))
                if value.is_import():
                    imports[path] = value[0]

        for path, obj in imports.items():
            fname = self.resolve(obj.file, _data)
            import_data = self.load(fname)
            if obj.replace:
                ConfigGetter.delete(_data, path)
                _data.update(import_data)
            else:
                ConfigGetter.set(_data, path, import_data)

        return _data

    def resolve(self, value, _data: Optional[Mapping] = None):
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

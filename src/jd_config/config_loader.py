#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Main config package to load and access config values.
"""

import os
import logging
from typing import Any, Mapping, Optional
from .placeholder import ImportPlaceholder, Placeholder
from .placeholder import CompoundValue
from .objwalk import objwalk
from .config_getter import ConfigGetter, ConfigException
from .yaml_loader import MyYamlLoader


__parent__name__ = __name__.rpartition('.')[0]
logger = logging.getLogger(__parent__name__)


class YamlFileLoaderMixin:
    """Load the yaml config files and process the placeholders
    """

    def __init__(self) -> None:
        """Initialize.
        """

        # The list of yaml files loaded
        self.files_loaded = []
        self.file_recursions = []


    def load_yaml_raw_fd(self, fd) -> Mapping:
        """Load a Yaml file with our Loader, but no post-processing

        :param fd: a file descriptor
        :return: A deep dict-like structure, representing the yaml content
        """
        loader = MyYamlLoader(fd)
        return loader.get_single_data()


    def load_yaml_raw(self, fname: os.PathLike) -> Mapping:
        """Load a Yaml file with our Loader, but no post-processing

        :param fname: the yaml file to load
        :return: A deep dict-like structure, representing the yaml content
        """

        # pyyaml will consider the BOM, if available,
        # and decode the bytes. utf-8 is default.
        logger.debug("Config: Load from file: '%s'", fname)
        with open(fname, "rb") as fd:
            return self.load_yaml_raw_fd(fd)


    def load(self,
        fname: Optional[os.PathLike] = None,
        config_dir: Optional[os.PathLike] = None
    ) -> Mapping:
        """Load a Yaml config file, and if an env var is defined, also load
        the environment specific overlay.
        """
        # Load the yaml file, including all imports
        _data = self.load_one_file(fname, config_dir)

        if self.env:
            try:
                fname, oldext = os.path.splitext(fname)
                fname = fname + "-" + self.env + oldext
                data_2 = self.load_one_file(fname, config_dir)
                _data.update(data_2)
            except FileNotFoundError:
                pass    # This is perfectly ok. The file may not exist.

        # Make the yaml config data accessible via JDConfig
        self.data = _data
        return _data

    def load_one_file(self,
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

        if isinstance(fname, str):
            if not os.path.isabs(fname):
                fname = os.path.join(config_dir, fname)

            fname = os.path.abspath(fname)
            if fname in self.file_recursions:
                raise ConfigException(
                    "File recursion. The following config file is recursively "
                    f"imported: '{fname}'")

            # self.file_recursions nicely shows the circle of imports
            # self.files_loaded is nice to see the sequence of loaded files.
            try:
                self.file_recursions.append(fname)
                self.files_loaded.append(fname)
                _data = self.load_yaml_raw(fname)
            except:     # pylint: disable=bare-except
                self.files_loaded.pop()
                raise

            _data = self.post_process(_data, config_dir)
            self.file_recursions.pop()

        else:
            # Assuming it is an IO stream of some sort
            self.files_loaded.append("<data>")
            _data = self.load_yaml_raw_fd(fname)
            _data = self.post_process(_data, config_dir)

        return _data

    def post_process(self, _data: Mapping, config_dir: os.PathLike) -> Mapping:
        """Replace '{..}' with Placeholders and execute imports if needed.

        :param _data: the yaml data loaded already
        :return: the updated yaml data with imports replaced.
        """

        imports: dict[Any, ImportPlaceholder] = {}
        for event in objwalk(_data, nodes_only=True):
            value = event.value.value
            if isinstance(value, str) and value.find("{") != -1:
                event.value.value = value = CompoundValue(self.value_reader.parse(value))
                if value.is_import():
                    imports[event.path] = value[0]

            if isinstance(value, Placeholder):
                value.post_load(_data)
            elif isinstance(value, list):
                for elem in value:
                    if isinstance(elem, Placeholder):
                        elem.post_load(_data)

        for path, obj in imports.items():
            fname = self.resolve(obj.file, _data)
            import_data = self.load(fname, config_dir)
            if obj.replace:
                ConfigGetter.delete(_data, path)
                _data.update(import_data)
            else:
                ConfigGetter.set(_data, path, import_data)

        return _data

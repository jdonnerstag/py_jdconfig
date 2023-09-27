#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Load yaml config files and handle the placeholders
"""

from io import StringIO
import logging
from pathlib import Path
from typing import Any, Mapping, Optional
from .placeholders import ImportPlaceholder, Placeholder
from .value_reader import CompoundValue
from .objwalk import objwalk
from .config_getter import ConfigGetter, ConfigException
from .yaml_loader import MyYamlLoader


__parent__name__ = __name__.rpartition('.')[0]
logger = logging.getLogger(__parent__name__)


class ConfigFileLoader:
    """Load the yaml config files and process the placeholders.

    Dependencies:
    - self.resolve(): a method to lazily resolve placeholders
    """

    def __init__(self, dependencies) -> None:
        """Initialize.
        """

        # An object that provides self.data and self.resolve()
        self.dependencies = dependencies

        # The list of yaml files loaded
        self.files_loaded = []
        self.file_recursions = []


    def make_filename(self, fname: Path, config_dir: Path, env: Optional[str] = None
            ) -> tuple[Path, Path]:
        """Make a filename from the parts"""

        if env:
            fname = fname.parent.joinpath(f"{fname.stem}-{env}{fname.suffix}")

        if config_dir and not fname.is_absolute():
            fname = config_dir.joinpath(fname)

        return fname


    def load(self, fname: Path|StringIO, config_dir: Path|None, env: str|None = None) -> Mapping:
        """Load a Yaml config file, and if an env var is defined, also load
        the environment specific overlay.
        """

        # If fname is a relative Path, then prepend the config_dir.
        # If fname is absolute, keep as is
        # If fname is StringIO, we don't want any modifications
        if isinstance(fname, Path):
            fname = self.make_filename(fname, config_dir=config_dir, env=None)

        data_1 = self.load_one_file(fname, config_dir)

        if env and isinstance(fname, Path):
            try:
                fname = self.make_filename(fname, config_dir=None, env=env)
                data_2 = self.load_one_file(fname, config_dir)

                # TODO Replace with deep_update()
                data_1.update(data_2)
            except FileNotFoundError:
                pass    # This is perfectly ok. The file may not exist.

        return data_1


    def load_one_file(self, fname: Path|StringIO, config_dir: Path) -> Mapping:
        """Load a Yaml config file, determine and load 'imports', and
        pre-process for efficient, yet lazy, key/value resolution.

        :param fname: the yaml file to load. Default: config file configured in config.ini
        """

        if isinstance(fname, Path):
            fname = fname.resolve(fname)

        if fname in self.file_recursions:
            raise ConfigException(
                "File recursion. The following config file is recursively "
                f"imported: '{fname}'")

        self.file_recursions.append(fname)

        if isinstance(fname, Path):
            # self.file_recursions nicely shows the circle of imports
            # self.files_loaded is nice to see the sequence of loaded files.
            try:
                self.files_loaded.append(fname)
                data = self.load_yaml_raw_with_filename(fname)
            except:     # pylint: disable=bare-except
                self.files_loaded.pop()
                raise

        else:
            # Assuming it is an IO stream of some sort
            self.files_loaded.append("<data>")
            data = self.load_yaml_raw_with_fd(fname)

        data = self.post_process(data, config_dir)
        self.file_recursions.pop()

        return data


    def load_yaml_raw_with_fd(self, fd) -> Mapping:
        """Load a Yaml file with our Loader, but no post-processing

        :param fd: a file descriptor
        :return: A deep dict-like structure, representing the yaml content
        """
        loader = MyYamlLoader(fd)
        return loader.get_single_data()


    def load_yaml_raw_with_filename(self, fname: Path) -> Mapping:
        """Load a Yaml file with our Loader, but no post-processing

        :param fname: the yaml file to load
        :return: A deep dict-like structure, representing the yaml content
        """

        # pyyaml will consider the BOM, if available,
        # and decode the bytes. utf-8 is default.
        logger.debug("Config: Load from file: '%s'", fname)
        with open(fname, "rb") as fd:
            return self.load_yaml_raw_with_fd(fd)


    def post_process(self, data: Mapping, config_dir: Path) -> Mapping:
        """Replace '{..}' with Placeholders and execute imports if needed.

        :param data: the yaml data loaded already
        :return: the updated yaml data with imports replaced.
        """

        imports: dict[Any, ImportPlaceholder] = {}
        for event in objwalk(data, nodes_only=True):
            self.post_process_node(data, event, imports)

        for path, obj in imports.items():
            self.exec_yaml_import(data, path, obj, config_dir)

        return data


    def post_process_node(self, data, event, imports):
        """Evaluate of the yaml string value contains a placeholder
        """
        assert hasattr(self.dependencies, "value_reader")
        assert hasattr(self.dependencies.value_reader, "parse")
        assert callable(self.dependencies.value_reader.parse)
        value_reader = self.dependencies.value_reader.parse

        value = event.value.value
        if isinstance(value, str) and value.find("{") != -1:
            event.value.value = value = CompoundValue(value_reader(value))
            if value.is_import():
                imports[event.path] = value[0]

        if isinstance(value, Placeholder):
            value.post_load(data)
        elif isinstance(value, list):
            for elem in value:
                if isinstance(elem, Placeholder):
                    elem.post_load(data)


    def exec_yaml_import(self, data, path, obj, config_dir):
        """Execute the Import placeholder and replace yaml value with the
        content from the imported yaml file
        """
        assert hasattr(self.dependencies, "resolve")
        assert callable(self.dependencies.resolve)

        fname = Path(self.dependencies.resolve(obj.file, data))
        import_data = self.load(fname, config_dir)
        if obj.replace:
            ConfigGetter.delete(data, path)
            data.update(import_data)
        else:
            ConfigGetter.set(data, path, import_data)

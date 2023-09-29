#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Load yaml config files and handle the placeholders
"""

from io import StringIO
import logging
from pathlib import Path
from typing import Mapping, Optional
from .placeholders import ImportPlaceholder, Placeholder
from .value_reader import CompoundValue
from .objwalk import objwalk
from .config_getter import ConfigGetter, ConfigException
from .yaml_loader import MyYamlLoader


__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


class ConfigFileLoader:
    """Load the yaml config files and process the placeholders.

    Dependencies:
    - self.resolve(): a method to lazily resolve placeholders
    """

    def __init__(self, dependencies) -> None:
        """Initialize."""

        # An object that provides self.data and self.resolve()
        self.dependencies = dependencies

        # The list of yaml files loaded
        self.files_loaded = []
        self.file_recursions = []

    def make_filename(
        self, fname: Path, config_dir: Path, env: Optional[str] = None
    ) -> tuple[Path, Path]:
        """Make a filename from the parts"""

        if env:
            fname = fname.parent.joinpath(f"{fname.stem}-{env}{fname.suffix}")

        if config_dir and not fname.is_absolute():
            fname = config_dir.joinpath(fname)

        return fname

    def load(
        self, fname: Path | StringIO, config_dir: Path | None, env: str | None = None
    ) -> Mapping:
        """Load a Yaml config file, and if an env var is defined, also load
        the environment specific overlay.
        """

        # If fname is a relative Path, then prepend the config_dir.
        # If fname is absolute, keep as is
        # If fname is StringIO, we don't want any modifications
        if isinstance(fname, Path):
            fname = self.make_filename(fname, config_dir=config_dir, env=None)

        data_1 = self.load_one_file(fname)
        data_2 = None

        if env and isinstance(fname, Path):
            try:
                fname = self.make_filename(fname, config_dir=None, env=env)
                data_2 = self.load_one_file(fname)

                data_2 = self.post_process_imports(data_2, None, config_dir)

            except FileNotFoundError:
                pass  # This is perfectly ok. The file may not exist.

        data_1 = self.post_process_imports(data_1, data_2, config_dir)

        if data_2:
            data_1 = ConfigGetter.deep_update(data_1, data_2)

        return data_1

    def load_one_file(self, fname: Path | StringIO) -> Mapping:
        """Load a Yaml config file, determine and load 'imports', and
        pre-process for efficient, yet lazy, key/value resolution.

        :param fname: the yaml file to load. Default: config file configured in
            config.ini
        """
        if isinstance(fname, Path):
            fname = fname.resolve(fname)

        if fname in self.file_recursions:
            raise ConfigException(
                "File recursion. The following config file is recursively "
                f"imported: '{fname}'"
            )

        self.file_recursions.append(fname)

        if isinstance(fname, Path):
            # self.file_recursions nicely shows the circle of imports
            # self.files_loaded is nice to see the sequence of loaded files.
            try:
                self.files_loaded.append(fname)
                data = self.load_yaml_raw_with_filename(fname)
            except:  # pylint: disable=bare-except
                self.files_loaded.pop()
                raise

        else:
            # Assuming it is an IO stream of some sort
            self.files_loaded.append("<data>")
            data = self.load_yaml_raw_with_fd(fname)

        data = self.post_process(data)

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

    def post_process(self, data: Mapping) -> Mapping:
        """Replace '{..}' with Placeholders and execute imports if needed.

        :param data: the yaml data loaded already
        :return: the updated yaml data with imports replaced.
        """

        assert hasattr(self.dependencies, "value_reader")
        assert hasattr(self.dependencies.value_reader, "parse")
        assert callable(self.dependencies.value_reader.parse)
        value_reader = self.dependencies.value_reader.parse

        for event in objwalk(data, nodes_only=True):
            value = event.value.value
            if isinstance(value, str) and value.find("{") != -1:
                event.value.value = value = CompoundValue(value_reader(value))

            if isinstance(value, list):
                for elem in value:
                    if isinstance(elem, Placeholder):
                        elem.post_load(data)

        return data

    def post_process_imports(self, data_1, data_2, config_dir):
        """Execute the Import placeholder and replace yaml value with the
        content from the imported yaml file
        """
        assert hasattr(self.dependencies, "resolve")
        assert callable(self.dependencies.resolve)

        for event in objwalk(data_1, nodes_only=True):
            value = event.value.value  # NodeEvent.YamlObj.value
            if not isinstance(value, list):
                continue

            for elem in value:
                if not isinstance(elem, ImportPlaceholder):
                    continue

                if len(value) != 1:
                    raise ConfigException(
                        "Illegal {import: ...} syntax. Only one elem "
                        f"allowed: {value}"
                    )

                fname = Path(self.dependencies.resolve(elem.file, data_1, data_2))
                import_data = self.load(fname, config_dir)
                ConfigGetter.set(data_1, event.path, import_data)

        self.file_recursions.pop()

        return data_1

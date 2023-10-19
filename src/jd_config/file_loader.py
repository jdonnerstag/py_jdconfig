#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Load yaml config files
"""

import logging
from io import StringIO
from pathlib import Path
from typing import Mapping, Optional

import yaml

from .deep_dict import DeepDict

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


class ConfigFileLoader:
    """Load the yaml config files."""

    def __init__(self) -> None:
        self.files_loaded = []

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

            except FileNotFoundError:
                pass  # This is perfectly ok. The file may not exist.

        if data_2:
            # Inplace update of data_1
            DeepDict(data_1).deep_update(data_2)

        return data_1

    def load_one_file(self, fname: Path | StringIO) -> Mapping:
        """Load a Yaml config file, determine and load 'imports', and
        pre-process for efficient, yet lazy, key/value resolution.

        :param fname: the yaml file to load. Default: config file configured in
            config.ini
        """
        if isinstance(fname, Path):
            fname = fname.resolve(fname)
            self.files_loaded.append(fname)
        else:
            self.files_loaded.append("<data>")

        if isinstance(fname, Path):
            # self.file_recursions nicely shows the circle of imports
            # self.files_loaded is nice to see the sequence of loaded files.
            data = self.load_yaml_raw_with_filename(fname)
        else:
            # Assuming it is an IO stream of some sort
            data = self.load_yaml_raw_with_fd(fname)

        return data

    def load_yaml_raw_with_fd(self, file_descriptor) -> Mapping:
        """Load a Yaml file with our Loader, but no post-processing

        :param fd: a file descriptor
        :return: A deep dict-like structure, representing the yaml content
        """
        return yaml.safe_load(file_descriptor)

    def load_yaml_raw_with_filename(self, fname: Path) -> Mapping:
        """Load a Yaml file with our Loader, but no post-processing

        :param fname: the yaml file to load
        :return: A deep dict-like structure, representing the yaml content
        """

        logger.debug("Config: Load from file: '%s'", fname)

        # pyyaml will consider the BOM, if available,
        # and decode the bytes. utf-8 is default.
        with open(fname, "rb") as fd:  # pylint: disable=invalid-name
            return self.load_yaml_raw_with_fd(fd)

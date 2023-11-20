#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Load yaml config files
"""

import logging
from io import StringIO
from pathlib import Path
from typing import Mapping, Optional, Sequence

import yaml

from .utils import ConfigException, relative_to_cwd

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


class ConfigFile(dict):
    """A config file"""

    def __init__(self, data: Mapping, file: Path | None) -> None:
        super().__init__(data)
        self.file = file


class ConfigFileLoader:
    """Load the yaml config files."""

    def make_filename(
        self, fname: Path, config_dir: str | Path, env: Optional[str] = None
    ) -> Path:
        """Make a filename from the parts"""

        if env:
            fname = fname.parent.joinpath(f"{fname.stem}-{env}{fname.suffix}")

        if config_dir and not fname.is_absolute():
            fname = Path(config_dir).joinpath(fname)

        return fname

    # pylint: disable=too-many-arguments
    def load(
        self,
        fname: Path | StringIO,
        config_dir: Path | Sequence[Path] | None,
        env: str | None = None,
    ) -> ConfigFile:
        """Load a Yaml config file, and if an env var is defined, also load
        the environment specific overlay.
        """

        # If fname is a relative Path, then prepend the config_dir.
        # If fname is absolute, keep as is
        # If fname is StringIO, we don't want any modifications

        # File name or stream?
        if not isinstance(fname, Path):
            data = self.load_one_file(fname)
            data = ConfigFile(data, "<data>")
            return data

        if config_dir is None:
            config_dir = [None]
        elif isinstance(config_dir, (str, Path)):
            config_dir = [Path(config_dir)]
        elif isinstance(config_dir, list):
            pass
        else:
            raise ConfigException(f"Bug: invalid 'config_dir': {config_dir}")

        orig_fname = fname
        for direc in config_dir:
            fname = self.make_filename(orig_fname, config_dir=direc, env=env)
            try:
                data = self.load_one_file(fname)
                data = ConfigFile(data, fname)
                return data
            except FileNotFoundError:
                pass  # This is perfectly ok. The file may not exist.

        raise FileNotFoundError(f"File not found: '{orig_fname}' in {config_dir}")

    def load_one_file(self, fname: Path | StringIO) -> Mapping:
        """Load a Yaml config file, determine and load 'imports', and
        pre-process for efficient, yet lazy, key/value resolution.

        :param fname: the yaml file to load. Default: config file configured in
            config.ini
        """

        if isinstance(fname, Path):
            fname = fname.resolve(fname)
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

        logger.debug("Config: Load from file: '%s'", relative_to_cwd(fname))

        # pyyaml will consider the BOM, if available,
        # and decode the bytes. utf-8 is default.
        with open(fname, "rb") as fd:  # pylint: disable=invalid-name
            data = self.load_yaml_raw_with_fd(fd)
            return data

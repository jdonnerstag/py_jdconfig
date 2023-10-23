#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Load yaml config files
"""

from collections import ChainMap
from dataclasses import dataclass
import logging
from io import StringIO
from pathlib import Path
from typing import Any, Iterator, Mapping, Optional, TYPE_CHECKING

import yaml

from .utils import ContainerType, relative_to_cwd

if TYPE_CHECKING:
    from .deep_getter import GetterContext

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


# pylint: disable=too-few-public-methods
class ConfigFileLoggerMixin:
    """Log a debug message if the key was found in the overlay file"""

    def cb_get(self, data, key, ctx: "GetterContext") -> Any:
        """Log a debug message if the key was found in the overlay file"""
        rtn = super().cb_get(data, key, ctx)

        if isinstance(data, ConfigFile) and data.file_2 is not None:
            if isinstance(data.data, ChainMap) and key in data.data.maps[0]:
                if ctx.key is None:
                    ctx.key = key
                    
                logger.debug(
                    "Found key %s in environment overlay: %s",
                    ctx.cur_path(),
                    relative_to_cwd(data.file_2),
                )

        return rtn


@dataclass
class ConfigFile(Mapping):
    """A config file and optional environment specifc overlay (dev, test, prod)"""

    file_1: Path | None  # Main file
    file_2: Path | None  # Env specific overlay
    data: Mapping  # The actual data: either dict or ChainMap of both files
    env: str | None  # The env name

    def __getitem__(self, key: str) -> Any:
        return self.data.__getitem__(key)

    def __iter__(self) -> Iterator:
        return self.data.__iter__()

    def __len__(self) -> int:
        return len(self.data)

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, ConfigFile):
            return False

        return self.file_1 == value.file_1 and self.file_2 == value.file_2


class ConfigFileLoader:
    """Load the yaml config files."""

    def __init__(self) -> None:
        self.env = None

        # List of all files loaded
        self.files_loaded = []

        # Cache files
        self.cache: dict[str, ContainerType] = {}

    def clear(self) -> None:
        """Clear the files list and the cache"""

        self.env = None
        self.files_loaded.clear()
        self.cache.clear()

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
        self,
        fname: Path | StringIO,
        config_dir: Path | None,
        env: str | None = None,
        cache: bool = True,
    ) -> ConfigFile:
        """Load a Yaml config file, and if an env var is defined, also load
        the environment specific overlay.
        """

        if self.env != env:
            if self.cache:
                logger.debug(
                    "Clearing file cache. Detected env change: %s != %s", self.env, env
                )

            # Clear any cached files associated with the previous env.
            self.clear()

        self.env = env

        # If fname is a relative Path, then prepend the config_dir.
        # If fname is absolute, keep as is
        # If fname is StringIO, we don't want any modifications
        if isinstance(fname, Path):
            fname = self.make_filename(fname, config_dir=config_dir, env=None)

        data_1 = self.load_one_file(fname, cache=cache)
        data_2 = None
        fname_1 = fname
        fname_2 = None

        if env and isinstance(fname, Path):
            try:
                fname = self.make_filename(fname, config_dir=None, env=env)
                data_2 = self.load_one_file(fname, cache=cache)
                fname_2 = fname

            except FileNotFoundError:
                pass  # This is perfectly ok. The file may not exist.

        if data_2:
            data = ChainMap(data_2, data_1)
        else:
            data = data_1

        return ConfigFile(
            file_1=fname_1,
            file_2=fname_2,
            data=data,
            env=env,
        )

    def load_one_file(self, fname: Path | StringIO, cache: bool = True) -> Mapping:
        """Load a Yaml config file, determine and load 'imports', and
        pre-process for efficient, yet lazy, key/value resolution.

        :param fname: the yaml file to load. Default: config file configured in
            config.ini
        """

        if not isinstance(self.cache, dict):
            cache = False

        if isinstance(fname, Path):
            fname = fname.resolve(fname)
            if cache and fname in self.cache:
                data = self.cache[fname]
            else:
                self.files_loaded.append(fname)
                data = self.load_yaml_raw_with_filename(fname)
                if cache:
                    self.cache[fname] = data
        else:
            # Assuming it is an IO stream of some sort
            self.files_loaded.append("<data>")
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

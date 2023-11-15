#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Load yaml config files
"""

import logging
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterator, Mapping, Optional, Sequence

import yaml

from .utils import ConfigException, ContainerType, relative_to_cwd

if TYPE_CHECKING:
    from .getter_context import GetterContext
    from .deep_getter import GetterFn

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


# pylint: disable=too-few-public-methods
class ConfigFileLoggerMixin:
    """Log a debug message if the key was found in the overlay file"""

    @staticmethod
    def cb_get(data, key: str | int, ctx: "GetterContext", next_fn: "GetterFn") -> Any:
        """Log a debug message if the key was found in the overlay file"""
        fn = next_fn()
        rtn = fn(data, key, ctx, next_fn)

        if isinstance(data, ConfigFile) and data.file_2 is not None:
            if key in data.data_2:
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

    file_1: Path  # Main file
    data_1: Mapping  # Data from main file

    file_2: Optional[Path]  # Env specific overlay
    data_2: Optional[Mapping]  # Data from overlay file

    data_3: Optional[Mapping]  # CLI arguments

    env: str | None  # The env name

    def __getitem__(self, key: str) -> Any:
        if self.data_3 is not None:
            try:
                return self.data_3[key]
            except:  # pylint: disable=bare-except
                pass

        if self.data_2 is not None:
            try:
                return self.data_2[key]
            except:  # pylint: disable=bare-except
                pass

        return self.data_1[key]

    def merge(self) -> dict:
        if not self.data_2 and not self.data_3:
            return self.data_1

        data = self.data_1.copy()
        if self.data_2:
            data.update(self.data_2)

        if self.data_3:
            data.update(self.data_3)

        return data

    def __iter__(self) -> Iterator:
        return self.merge().__iter__()

    def __len__(self) -> int:
        return len(self.merge())

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, ConfigFile):
            return False

        return (
            self.file_1 == value.file_1
            and self.file_2 == value.file_2
            and self.data_3 == value.data_3
        )

    def add_cli_args(self, values: Mapping) -> None:
        self.data_3 = values


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
        self, fname: Path, config_dir: str | Path, env: Optional[str] = None
    ) -> tuple[Path, Path]:
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
        config_dir: Path | None,
        env: str | None = None,
        cache: bool = True,
        add_env_dirs: Optional[Sequence[str | Path] | str | Path] = None,
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
        orig_fname = fname
        if isinstance(fname, Path):
            fname = self.make_filename(orig_fname, config_dir=config_dir, env=None)

        try:
            data_1 = self.load_one_file(fname, cache=cache)
        except FileNotFoundError as exc:
            raise ConfigException(f"Config file not found: '{fname}'") from exc

        data_2 = None
        fname_1 = fname
        fname_2 = None

        if env and isinstance(fname, Path):
            if add_env_dirs is None:
                add_env_dirs = [config_dir]
            elif isinstance(add_env_dirs, (str, Path)):
                add_env_dirs = [config_dir, Path(add_env_dirs)]
            elif isinstance(add_env_dirs, list):
                add_env_dirs.append(config_dir)
            else:
                raise ConfigException(f"Bug: invalid 'add_env_dirs': {add_env_dirs}")

            for cfg_dir in add_env_dirs:
                try:
                    fname = self.make_filename(orig_fname, config_dir=cfg_dir, env=env)
                    data_2 = self.load_one_file(fname, cache=cache)
                    fname_2 = fname
                    break

                except FileNotFoundError:
                    pass  # This is perfectly ok. The file may not exist.

        return ConfigFile(
            file_1=fname_1,
            file_2=fname_2,
            data_1=data_1,
            data_2=data_2,
            data_3=None,
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

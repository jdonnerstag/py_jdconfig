#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Mixin to load "system" configs from config.ini
"""

import configparser
import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path

from .string_converter_mixin import StringConverterMixin
from .utils import ConfigException, relative_to_cwd

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


class EnvInterpolation(configparser.BasicInterpolation):
    """Interpolation which expands environment variables in values."""

    # pylint: disable=:too-many-arguments
    def before_get(self, parser, section, option, value, defaults):
        value = super().before_get(parser, section, option, value, defaults)
        return os.path.expandvars(value)


@dataclass
class IniData:
    """[config] section in ini-file"""

    config_dir: str = "."
    config_file: str = "config.yaml"
    default_env: str | None = None
    env: str | None = None
    add_env_dirs: list[Path] | None = None


# pylint: disable=too-few-public-methods
class ConfigIniMixin:
    """A mixin to load the Config specific configurations."""

    def __init__(
        self, *, ini_env: str | None = None, ini_file: str | None = "config.ini"
    ) -> None:
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

        config = configparser.ConfigParser(
            interpolation=EnvInterpolation(), allow_no_value=True
        )

        if ini_env and not ini_file:
            ini_file = os.environ.get(ini_env, None)

        self.ini_file = ini_file
        self.ini_env_var = ini_env

        if ini_file:
            logger.debug("Config: Load ini-file: '%s'", relative_to_cwd(ini_file))
            try:
                self.ini_file = ini_file = Path(ini_file).resolve()
                config.read(ini_file)
            except FileNotFoundError as exc:
                raise ConfigException(f"Ini-file not found: '{ini_file}'") from exc

        self.ini = IniData()

        try:
            config = config["config"]

            self.ini.config_dir = config.get("config_dir", ".")
            self.ini.config_file = config.get("config_file", "config.yaml")
            self.ini.default_env = config.get("default_env", None)
            self.ini.env = config.get("env", self.ini.default_env)
            add_env_dirs = config.get("add_env_dirs", None)

            if self.ini.env and self.ini.env.startswith("$"):
                logger.debug(
                    "ENV variable not defined: '%s'. Applying default: '%s'",
                    self.ini.env,
                    self.ini.default_env,
                )
                self.ini.env = self.ini.default_env

            if add_env_dirs is not None:
                self.ini.add_env_dirs = json.loads(add_env_dirs)

        except KeyError:
            pass

        if self.ini.add_env_dirs is None:
            self.ini.add_env_dirs = [Path.cwd()]

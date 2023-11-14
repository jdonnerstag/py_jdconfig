#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Load config settings from *.ini
"""

from  configparser import ConfigParser, BasicInterpolation, SectionProxy
import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

from .utils import ConfigException, relative_to_cwd

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


class EnvInterpolation(BasicInterpolation):
    """Interpolation which expands environment variables $var and ${var} in values."""

    # pylint: disable=:too-many-arguments
    def before_get(self, parser, section, option, value, defaults):
        value = super().before_get(parser, section, option, value, defaults)
        return os.path.expandvars(value)


@dataclass
class IniData:
    """[config] section in ini-file"""

    # Make all section variable available
    config: SectionProxy | None

    # Working directory to load config files
    config_dir: str = "."

    # Default config file name
    config_file: str = "config.yaml"

    # The environment name, e.g. dev, test, qa, prod,...
    # if not overwritten elsewhere (e.g. cli)
    env: str | None = None

    # List of directories to search for env specific overlay files
    env_dirs: list[Path] = field(default_factory=lambda: [Path.cwd()])


# pylint: disable=too-few-public-methods
class ConfigIni:
    """Load config settings from *.ini"""

    def read_file(self, ini_file: str = "config.ini") -> (ConfigParser, Path):
        """Read the ini-file with customized parser"""

        # Support
        # - Environment Variable resolution in the ini-file
        # - Support comment lines (via allow_no_value)
        config = ConfigParser(
            interpolation=EnvInterpolation(), allow_no_value=True
        )

        if ini_file:
            logger.debug("Config: Load ini-file: '%s'", relative_to_cwd(ini_file))
            ini_file = Path(ini_file).resolve()
            if not ini_file.is_file():
                raise ConfigException(f"Ini-file not found: '{ini_file}'")

            config.read(ini_file)

        return config, ini_file

    def _update_if_present(self, ini, section, name):
        value = section.get(name, None)
        if value is not None:
            setattr(ini, name, value)

        return value

    def load(
        self, ini_file: str = "config.ini", ini_section: str = "config"
    ) -> (IniData, Path):
        """Load config related system settings from a section of an ini-file.

        We distinguish between system and user settings. The ini-file is only
        used for config related system settings. E.g.

        ```
        [config]
        config_dir = .
        config_file = config.yaml
        env = prod
        env_dirs = ["."]
        ```

        Some of the JDConfig configs determine where to find the user
        specific configurations files, including environment specific
        overlays.

        :param ini_file: Path to JDConfig config file. Default: 'config.ini'
        """

        if ini_file is None:
            return IniData(None), None

        config, ini_file = self.read_file(ini_file)

        try:
            section = config[ini_section]
        except KeyError as exc:
            raise ConfigException(
                f"Ini-file section not found: '{ini_section}' in '{ini_file}'"
            ) from exc

        ini = IniData(section, **section)

        # self._update_if_present(ini, config, "config_dir")
        # self._update_if_present(ini, config, "config_file")

        # self._update_if_present(ini, config, "env")
        if ini.env and ini.env.startswith("$"):
            raise ConfigException("Missing ENV variable '{ini.env}' in '{ini_file}'")

        # env_dirs = config.get("env_dirs", None)
        if ini.env_dirs is None:
            ini.env_dirs = [Path.cwd()]
        elif isinstance(ini.env_dirs, str):
            ini.env_dirs = json.loads(ini.env_dirs)

        return ini, ini_file

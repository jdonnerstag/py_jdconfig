#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Mixin to load "system" configs from config.ini
"""

import configparser
import logging
import os

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


class EnvInterpolation(configparser.BasicInterpolation):
    """Interpolation which expands environment variables in values."""

    # pylint: disable=:too-many-arguments
    def before_get(self, parser, section, option, value, defaults):
        value = super().before_get(parser, section, option, value, defaults)
        return os.path.expandvars(value)


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
        resolve_eagerly = False
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

        if ini_file:
            logger.debug("Config: Load ini-file: '%s'", ini_file)
            config.read(ini_file)

        try:
            config = config["config"]
        except KeyError:
            config = {}

        self.ini = {}
        self.ini["config_dir"] = config.get("config_dir", ".")
        self.ini["config_file"] = config.get("config_file", "config.yaml")
        self.ini["default_env"] = config.get("default_env", None)
        self.ini["env"] = config.get("env", self.ini.get("default_env", None))
        self.ini["resolve_eagerly"] = bool(config.get("resolve_eagerly", False))

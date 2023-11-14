#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C

import logging
import os
from pathlib import Path

import pytest

from jd_config import ConfigException, ConfigIni

logger = logging.getLogger(__name__)

# Notes:
# show logs: pytest --log-cli-level=DEBUG


def test_jdconfig_config_ini(monkeypatch):
    monkeypatch.setenv("MY_ENV", "jd_dev")

    # ini_file = None => Apply system defaults
    cfg, _ = ConfigIni().load(ini_file=None)
    assert cfg.config_dir == "."
    assert cfg.config_file == "config.yaml"
    assert cfg.env is None
    assert cfg.env_dirs == [Path.cwd()]

    ini_file = os.path.join(os.path.dirname(__file__), "data", "config.ini")
    cfg, _ = ConfigIni().load(ini_file=ini_file)
    assert cfg.config_dir == "./configs-1"
    assert cfg.config_file == "main_config.yaml"
    assert cfg.env == "jd_dev"  # validate that ini value interpolation works
    assert cfg.env_dirs == ["."]

    with pytest.raises(ConfigException):
        ConfigIni().load(ini_file, "not-existing-section")

    with pytest.raises(ConfigException):
        ConfigIni().load("file_does_not_exist.ini")

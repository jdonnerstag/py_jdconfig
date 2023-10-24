#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C

import logging
import os

from jd_config import ConfigIniMixin

logger = logging.getLogger(__name__)

# Notes:
# show logs: pytest --log-cli-level=DEBUG


def test_jdconfig_config_ini(monkeypatch):
    monkeypatch.setenv("MY_ENV", "jd_dev")

    # ini_file = None => Apply system defaults
    cfg = ConfigIniMixin(ini_file=None)
    assert cfg.ini.config_dir == "."
    assert cfg.ini.config_file == "config.yaml"
    assert cfg.ini.env is None
    assert cfg.ini.default_env is None

    # ini_file = None => Apply system defaults
    ini_file = os.path.join(os.path.dirname(__file__), "data", "config.ini")
    cfg = ConfigIniMixin(ini_file=ini_file)
    assert cfg.ini.config_dir == "./configs-1"
    assert cfg.ini.config_file == "main_config.yaml"
    assert cfg.ini.env == "jd_dev"  # validate that ini value interpolation works
    assert cfg.ini.default_env == "dev"

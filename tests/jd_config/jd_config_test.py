#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C

import os
import logging
from jd_config import JDConfig, ConfigGetter

logger = logging.getLogger(__name__)

# Notes:
# show logs: pytest --log-cli-level=DEBUG

def test_jdconfig_config_ini():

    # ini_file = None => Apply system defaults
    cfg = JDConfig(ini_file=None)
    assert cfg.config_dir == "."
    assert cfg.config_file == "config.yaml"
    assert cfg.env_var == None
    assert cfg.default_env == "prod"

    # ini_file = None => Apply system defaults
    ini_file = os.path.join(os.path.dirname(__file__), "data", "config.ini")
    cfg = JDConfig(ini_file=ini_file)
    assert cfg.config_dir == "./configs-1"
    assert cfg.config_file == "main_config.yaml"
    assert cfg.env_var == "MY_ENV"
    assert cfg.default_env == "dev"

def data_dir(*args):
    return os.path.join(os.path.dirname(__file__), "data", *args)

def test_load_jdconfig_1():
    # config-1 contains a simple config file, with no imports.

    # Use the config.ini configs to load the config files
    cfg = JDConfig(ini_file = None)
    cfg.config_dir = data_dir("configs-1")
    cfg.config_file = "config.yaml"
    cfg.default_env = "dev"

    data = cfg.load()
    assert data

    # Provide the config file name. Note, that it'll not change or set the
    # config_dir. Any config files imported, are imported relativ to the
    # config_dir configured (or preset) in config.ini
    cfg = JDConfig(ini_file = None)
    file = data_dir("configs-1", "config.yaml")
    data = cfg.load(file)
    assert data

    # Provide a filename and a config_dir. All config imports, will be executed
    # relativ to the config_dir provided.
    # The config file might still be relativ or absolut.
    cfg = JDConfig(ini_file = None)
    config_dir = data_dir("configs-1")
    data = cfg.load("config.yaml", config_dir)
    assert data

    file = os.path.abspath(data_dir("configs-1", "config.yaml"))
    data = cfg.load(file, config_dir)
    assert data


def test_load_jdconfig_2():
    # config-2 is using some import placeholders, including dynamic ones,
    # where the actually path refers to config value.

    # Apply config_dir to set working directory for relativ yaml imports
    cfg = JDConfig(ini_file = None)
    config_dir = data_dir("configs-2")
    data = cfg.load("main_config.yaml", config_dir)
    assert data

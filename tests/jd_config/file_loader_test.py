#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C

import logging
import os
from pathlib import Path

from jd_config import ConfigFileLoader

logger = logging.getLogger(__name__)

# Notes:
# show logs: pytest --log-cli-level=DEBUG


def data_dir(*args) -> Path:
    path = os.path.join(os.path.dirname(__file__), "data", *args)
    path = Path(path).relative_to(Path.cwd())
    return path


def test_load_jdconfig_1():
    # config-1 contains a simple config file, with no imports.

    cfg = ConfigFileLoader()
    data = cfg.load(Path("config.yaml"), config_dir=data_dir("configs-1"))
    assert data
    assert data.file_1.parts[-1] == "config.yaml"
    assert data.file_2 is None
    assert data.data

    # With an absolute filename, the config_dir is ignored. Which however
    # only works as long as no {import: ..} placeholders are used.
    cfg = ConfigFileLoader()
    file = data_dir("configs-1", "config.yaml")
    data = cfg.load(file.absolute(), config_dir=Path("/this/likely/does/not/exist"))
    assert data

    # It shouldn't matter
    data = cfg.load(file.absolute(), config_dir=None)
    assert data


def test_separate_env_dir():
    # Config-6 is all about env specific overlay files.

    cfg_file = Path("config.yaml")
    config_dir = data_dir("configs-6")
    cfg = ConfigFileLoader()

    cfg_file = Path("config.yaml")
    env = None
    env_dirs = None
    data = cfg.load(cfg_file, config_dir=config_dir, env=env, add_env_dirs=env_dirs)
    assert data
    assert data.file_1.parts[-1] == "config.yaml"
    assert data.file_2 is None
    assert data.data

    cfg_file = Path("config.yaml")
    env = "missing"
    env_dirs = None
    data = cfg.load(cfg_file, config_dir=config_dir, env=env, add_env_dirs=env_dirs)
    assert data
    assert data.file_1.parts[-1] == "config.yaml"
    assert data.file_2 is None
    assert data.data

    cfg_file = Path("config.yaml")
    env = "dev"
    env_dirs = None
    data = cfg.load(cfg_file, config_dir=config_dir, env=env, add_env_dirs=env_dirs)
    assert data
    assert data.file_1.parts[-1] == "config.yaml"
    assert data.file_2.parts[-1] == "config-dev.yaml"
    assert data.data

    cfg_file = Path("config-2.yaml")
    env = "dev"
    env_dirs = None
    data = cfg.load(cfg_file, config_dir=config_dir, env=env, add_env_dirs=env_dirs)
    assert data
    assert data.file_1.parts[-1] == "config-2.yaml"
    assert data.file_2 is None
    assert data.data

    cfg_file = Path("config-2.yaml")
    env = "qa"
    env_dirs = None
    data = cfg.load(cfg_file, config_dir=config_dir, env=env, add_env_dirs=env_dirs)
    assert data
    assert data.file_1.parts[-1] == "config-2.yaml"
    assert data.file_2.parts[-1] == "config-2-qa.yaml"
    assert data.data

    cfg_file = Path("config-2.yaml")
    env = "qa"
    env_dirs = ["."]
    data = cfg.load(cfg_file, config_dir=config_dir, env=env, add_env_dirs=env_dirs)
    assert data
    assert data.file_1.parts[-1] == "config-2.yaml"
    assert data.file_2.parts[-1] == "config-2-qa.yaml"
    assert data.data

    cfg_file = Path("config-2.yaml")
    env = "dev-2"
    env_dirs = ["."]
    data = cfg.load(cfg_file, config_dir=config_dir, env=env, add_env_dirs=env_dirs)
    assert data
    assert data.file_1.parts[-1] == "config-2.yaml"
    assert data.file_2 is None
    assert data.data

    cfg_file = Path("config-2.yaml")
    env = "qa"
    env_dirs = [".", os.path.join(config_dir, "env_files")]
    data = cfg.load(cfg_file, config_dir=config_dir, env=env, add_env_dirs=env_dirs)
    assert data
    assert data.file_1.parts[-1] == "config-2.yaml"
    assert data.file_2.parts[-1] == "config-2-qa.yaml"
    assert data.data

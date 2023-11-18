#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C

import logging
import os
from pathlib import Path

import pytest

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
    assert data.file.parts[-1] == "config.yaml"

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

    config_dir = data_dir("configs-6")
    cfg = ConfigFileLoader()

    cfg_file = Path("config.yaml")
    data = cfg.load(cfg_file, config_dir=config_dir, env=None)
    assert data.file.parts[-1] == "config.yaml"

    cfg_file = Path("config.yaml")
    data = cfg.load(cfg_file, config_dir=[config_dir], env=None)
    assert data.file.parts[-1] == "config.yaml"

    cfg_file = Path("config.yaml")
    with pytest.raises(FileNotFoundError):
        cfg.load(cfg_file, config_dir=[config_dir], env="missing")

    cfg_file = Path("config.yaml")
    data = cfg.load(cfg_file, config_dir=[config_dir], env="dev")
    assert data.file.parts[-1] == "config-dev.yaml"

    cfg_file = Path("config.yaml")
    env_dirs = [config_dir, ".", os.path.join(config_dir, "env_files")]
    data = cfg.load(cfg_file, config_dir=env_dirs, env="dev-2")
    assert data.file.parts[-1] == "config-dev-2.yaml"

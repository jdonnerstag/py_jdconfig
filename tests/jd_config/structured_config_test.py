#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C

import logging
import os
from pathlib import Path
from pydantic import BaseModel

from jd_config import JDConfig

logger = logging.getLogger(__name__)

# Notes:
# show logs: pytest --log-cli-level=DEBUG


def data_dir(*args) -> Path:
    return Path(os.path.join(os.path.dirname(__file__), "data", *args))


class AppMetaConfig(BaseModel):
    version: str  # TODO define type that matches 0.6.0
    contact: str  # TODO define email type
    git_repo: str  # TODO define github repo type


class AppConfig(BaseModel):
    input_directory: str
    crm_database: str
    logging: "LoggingConfig"


class LoggingConfig(BaseModel):
    xyz: str


class MyConfig(BaseModel):
    app_meta: AppMetaConfig
    app: AppConfig


def test_load_structured_from_7():
    # config-4 is about simple {import:}, {ref:} and {global:}

    cfg = JDConfig(ini_file=None)
    cfg.ini.env = None  # Make sure, we are not even trying to load an env file
    cfg.ini.config_dir = data_dir("configs-7")  # configure the directory for imports
    data = cfg.load("config.yaml")
    assert data

    app_meta = cfg.get_into("app_meta", into=AppMetaConfig)
    assert isinstance(app_meta, AppMetaConfig)
    assert app_meta.version == "0.6.0"
    assert app_meta.contact == "peter.pan@neverland.com"
    assert app_meta.git_repo == "https://github.com/peter.pan/myapp"

    app = cfg.get_into("app", into=AppConfig)
    assert isinstance(app, AppConfig)
    assert app.input_directory == "./user_data"
    assert app.crm_database == "xyz@postgres"
    assert app.logging.xyz == "abc"

    app = cfg.get_into("", into=MyConfig)
    assert isinstance(app, MyConfig)
    assert isinstance(app.app_meta, AppMetaConfig)
    assert app.app_meta.version == "0.6.0"
    assert app.app_meta.contact == "peter.pan@neverland.com"
    assert app.app_meta.git_repo == "https://github.com/peter.pan/myapp"

    assert isinstance(app.app, AppConfig)
    assert app.app.input_directory == "./user_data"
    assert app.app.crm_database == "xyz@postgres"
    assert app.app.logging.xyz == "abc"

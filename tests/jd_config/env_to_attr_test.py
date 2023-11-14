#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C

from dataclasses import dataclass
import logging
import os

import pytest

from jd_config.env_to_attr import load_env_into_attr

logger = logging.getLogger(__name__)

# Notes:
# show logs: pytest --log-cli-level=DEBUG


class AppConfig:
    DEBUG: bool = False
    ENV: str = "production"
    API_KEY: str
    HOSTNAME: str
    PORT: int


def test_env_to_attr(monkeypatch):
    # API_KEY is required
    with pytest.raises(AttributeError):
        load_env_into_attr(AppConfig, {})

    monkeypatch.setenv("ENV", "dev")
    monkeypatch.setenv("API_KEY", "111")
    monkeypatch.setenv("HOSTNAME", "me.com")
    monkeypatch.setenv("PORT", "2222")

    app = load_env_into_attr(AppConfig, os.environ)
    assert app.ENV == "dev"
    assert app.DEBUG is False
    assert app.API_KEY == "111"
    assert app.HOSTNAME == "me.com"
    assert app.PORT == 2222


@dataclass
class DataConfig:
    API_KEY: str
    HOSTNAME: str
    PORT: int
    DEBUG: bool = False
    ENV: str = "production"


def test_dataclass(monkeypatch):
    monkeypatch.setenv("ENV", "dev")
    monkeypatch.setenv("API_KEY", "111")
    monkeypatch.setenv("HOSTNAME", "me.com")
    monkeypatch.setenv("PORT", "2222")

    app = load_env_into_attr(AppConfig, os.environ)
    assert app.ENV == "dev"
    assert app.DEBUG is False
    assert app.API_KEY == "111"
    assert app.HOSTNAME == "me.com"
    assert app.PORT == 2222

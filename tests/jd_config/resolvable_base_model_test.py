#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C

from io import StringIO
import logging
import os
from pathlib import Path

from jd_config.config_base_model import ConfigMeta
from jd_config.file_loader import ConfigFile, ConfigFileLoader

from jd_config.resolvable_base_model import ResolvableBaseModel
from jd_config.value_reader import ValueReader

logger = logging.getLogger(__name__)

# Notes:
# show logs: pytest --log-cli-level=DEBUG


def data_dir(*args) -> Path:
    return Path(os.path.join(os.path.dirname(__file__), "data", *args))


class A(ResolvableBaseModel):
    a: str
    b: str
    c: str


class App:
    value_reader: ValueReader = ValueReader()

    def load_import(
        self,
        fname: Path | StringIO,
        cache: bool = True,
    ) -> ConfigFile:
        return ConfigFileLoader().load(fname, data_dir("configs-4"))


def test_simple():
    data = dict(
        a="a",
        b="{ref:a}",
        c="{ref:b}",
    )

    meta = ConfigMeta(app=App(), data=data)
    app = A(meta=meta)
    assert app
    assert app.a == "a"
    assert app.b == "a"
    assert app.c == "a"

    app.a = "aa"
    assert app.a == "aa"
    assert app.b == "aa"
    assert app.c == "aa"


class Config4_2(ResolvableBaseModel):
    a: str
    b: str
    c: str
    d: str
    e: str
    f: str


class Config4(ResolvableBaseModel):
    a: str
    b: str
    c: Config4_2
    d: str
    e: str
    f: str


def test_import():
    app = App()
    data = app.load_import(Path("config.yaml"))
    meta = ConfigMeta(app=app, data=data)
    app = Config4(meta=meta)
    assert app
    assert app.a == "aa"
    assert app.b == "aa"
    assert app.c.a == "2aa"
    assert app.c.b == "2aa"
    assert app.c.c == "aa"
    assert app.c.d == "2aa"
    assert app.c.e == "aa"
    assert app.c.f == "aa"
    assert app.d == "2aa"
    assert app.e == "2aa"
    assert app.f == "aa"

    app.a = "AA"
    assert app.a == "AA"
    assert app.b == "AA"
    assert app.c.a == "2aa"
    assert app.c.b == "2aa"
    assert app.c.c == "AA"
    assert app.c.d == "2aa"
    assert app.c.e == "AA"
    assert app.c.f == "AA"
    assert app.d == "2aa"
    assert app.e == "2aa"
    assert app.f == "AA"

    app.b = "BB"
    assert app.a == "AA"
    assert app.b == "BB"
    assert app.c.a == "2aa"
    assert app.c.b == "2aa"
    assert app.c.c == "AA"
    assert app.c.d == "2aa"
    assert app.c.e == "BB"
    assert app.c.f == "AA"
    assert app.d == "2aa"
    assert app.e == "2aa"
    assert app.f == "AA"


class A2(ResolvableBaseModel):
    a: str
    b: str = "2"
    c: str = 3  # It will auto-convert to str type


def test_descriptor_with_default_value():
    data = dict(
        a="a",
    )

    meta = ConfigMeta(app=App(), data=data)
    app = A2(meta=meta)
    assert app
    assert app.a == "a"
    assert app.b == "2"
    assert app.c == "3"  # auto-converted to str

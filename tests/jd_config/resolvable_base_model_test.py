#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C

import dataclasses
from io import StringIO
import logging
import os
from pathlib import Path
import re
from typing import Optional

from jd_config.config_base_model import BaseModel, ModelMeta, ModelFile
from jd_config.file_loader import ConfigFile, ConfigFileLoader

from jd_config.resolvable_base_model import ResolvableBaseModel
from jd_config.utils import ContainerType
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

    meta = ModelMeta(app=App(), data=data)
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
    meta = ModelMeta(app=app, data=data)
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


class B(ResolvableBaseModel):
    a: A
    b: str
    c: str
    d: str
    e: str


def test_global_ref():
    data = dict(
        a=dict(a="aa", b="{ref:a}", c="{global:d}"),
        b="{ref:a}",
        c="{ref:a.a}",
        d="dd",
        e="{ref:a.c}",
    )

    meta = ModelMeta(app=App(), data=data)
    app = B(meta=meta)

    # To test {global:} without {import:}, we need to tune the loaded
    # data a little, and fake that an import happened.
    app.a.new_meta(None, model_obj=app.a, data=data["a"])

    assert app
    assert app.a.a == "aa"
    assert app.a.b == "aa"
    assert app.a.c == "dd"
    assert app.b.to_dict() == dict(a="aa", b="aa", c="dd")
    assert app.c == "aa"
    assert app.d == "dd"
    assert app.e == "dd"


def test_timestamp():
    data = dict(
        a="{timestamp: %Y%m%d-%H%M%S}",
        b="bb",
        c="cc",
    )

    meta = ModelMeta(app=App(), data=data)
    app = A(meta=meta)
    assert app
    assert re.match(r"\d{8}-\d{6}", app.a)

    # TODO Need to improve error reporting if timestamp fails parsing/format


def test_env_var(monkeypatch):
    monkeypatch.setenv("MY_ENV", "jd_dev")

    data = dict(
        a="{env: MY_ENV}",
        b="bb",
        c="cc",
    )

    meta = ModelMeta(app=App(), data=data)
    app = A(meta=meta)
    assert app
    assert app.a == "jd_dev"


def test_dev_env():
    pass  # TODO

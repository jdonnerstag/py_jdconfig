#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C

import os
from io import StringIO
import logging
from dataclasses import dataclass
from pathlib import Path

import pytest

from jd_config import (
    DEFAULT,
    EnvPlaceholder,
    GlobalRefPlaceholder,
    ImportPlaceholder,
    Placeholder,
    RefPlaceholder,
)
from jd_config.config_base_model import ModelMeta
from jd_config.file_loader import ConfigFile, ConfigFileLoader
from jd_config.resolvable_base_model import MissingConfigException, ResolvableBaseModel
from jd_config.value_reader import ValueReader

logger = logging.getLogger(__name__)

# Notes:
# show logs: pytest --log-cli-level=DEBUG


def test_ImportPlaceholder():
    obj = ImportPlaceholder(file="xxx")
    assert obj.file == "xxx"

    # Filename is missing
    with pytest.raises(Exception):
        ImportPlaceholder(file="")


def test_RefPlaceholder():
    obj = RefPlaceholder(path="db")
    assert obj.path == "db"
    assert obj.default_val is None

    # Filename is missing
    with pytest.raises(Exception):
        RefPlaceholder(path="")


def test_GlobalRefPlaceholder():
    obj = GlobalRefPlaceholder(path="db")
    assert obj.path == "db"
    assert obj.default_val is None

    # Filename is missing
    with pytest.raises(Exception):
        RefPlaceholder(path="")


def test_EnvPlaceholder(monkeypatch):
    obj = EnvPlaceholder(env_var="ENV")
    assert obj.env_var == "ENV"
    assert obj.default_val is DEFAULT

    # Filename is missing
    with pytest.raises(Exception):
        EnvPlaceholder(env_var="")

    monkeypatch.setenv("ENV", "this is a test")

    env = EnvPlaceholder("ENV")
    assert env.resolve(None, None) == "this is a test"


class A(ResolvableBaseModel):
    a: str
    b: str
    c: str = "cc"
    d: str = "dd"


def data_dir(*args) -> Path:
    return Path(os.path.join(os.path.dirname(__file__), "data", *args))


class App:
    value_reader: ValueReader = ValueReader()

    def load_import(
        self,
        fname: Path | StringIO,
        cache: bool = True,
    ) -> ConfigFile:
        return ConfigFileLoader().load(fname, data_dir("configs-4"))


def test_resolve():
    cfg = {
        "a": "aa",
        "b": "{ref:a}",
        "c": "{ref:b}",
        "d": "{ref:xxx}",
    }

    meta = ModelMeta(app=App(), data=cfg)
    model = A(meta=meta)
    ref = RefPlaceholder("a")
    assert ref.resolve(model, str) == "aa"

    ref = RefPlaceholder("b")
    assert ref.resolve(model, str) == "aa"

    ref = RefPlaceholder("c")
    assert ref.resolve(model, str) == "aa"

    ref = RefPlaceholder("d")
    with pytest.raises(AttributeError):
        ref.resolve(model, str)

    ref = RefPlaceholder("xxx")
    with pytest.raises(AttributeError):
        ref.resolve(model, str)


def test_global_ref():
    cfg = {
        "a": "aa",
        "b": "{global:a}",
        "c": "{global:b}",
        "d": "{global:xxx}",
    }

    meta = ModelMeta(app=App(), data=cfg)
    model = A(meta=meta)
    ref = GlobalRefPlaceholder("a")
    assert ref.resolve(model, str) == "aa"

    ref = GlobalRefPlaceholder("b")
    assert ref.resolve(model, str) == "aa"

    ref = GlobalRefPlaceholder("c")
    assert ref.resolve(model, str) == "aa"

    ref = GlobalRefPlaceholder("d")
    with pytest.raises(AttributeError):
        ref.resolve(model, str)

    ref = GlobalRefPlaceholder("xxx")
    with pytest.raises(AttributeError):
        ref.resolve(model, str)


@dataclass
class MyBespokePlaceholder(Placeholder):
    # This is also a test for a placeholder that does not take any parameters

    def resolve(self, *_, **__):
        return "it's me"


def test_bespoke_placeholder():
    cfg = {
        "a": "{ref:b}",
        "b": "{bespoke:}",
    }

    app = App()
    app.value_reader.registry["bespoke"] = MyBespokePlaceholder
    meta = ModelMeta(app=app, data=cfg)
    model = A(meta=meta)
    ref = RefPlaceholder("a")
    assert ref.resolve(model, str) == "it's me"


def test_mandatory_value():
    cfg = {
        "a": "???",
        "b": "{ref:a}",
    }

    meta = ModelMeta(app=App(), data=cfg)
    model = A(meta=meta)
    ref = RefPlaceholder("a")
    with pytest.raises(MissingConfigException):
        assert ref.resolve(model, str)

    ref = RefPlaceholder("b")
    with pytest.raises(MissingConfigException):
        assert ref.resolve(model, str)


def test_detect_recursion():
    cfg = {
        "a": "{ref:b}",
        "b": "{ref:c}",
        "c": "{ref:a}",
    }

    meta = ModelMeta(app=App(), data=cfg)
    model = A(meta=meta)
    ref = RefPlaceholder("a")
    with pytest.raises(RecursionError):
        assert ref.resolve(model, str)

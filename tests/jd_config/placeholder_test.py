#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C

import logging
from dataclasses import dataclass

import pytest

from jd_config import (
    DEFAULT,
    ConfigException,
    EnvPlaceholder,
    GlobalRefPlaceholder,
    ImportPlaceholder,
    Placeholder,
    RefPlaceholder,
    ResolverMixin,
)
from jd_config.base_model import BaseModel

logger = logging.getLogger(__name__)

# Notes:
# show logs: pytest --log-cli-level=DEBUG


class MyClass(ResolverMixin, BaseModel):
    pass


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

    model = MyClass({})
    env = EnvPlaceholder("ENV")
    assert env.resolve(model, None) == "this is a test"


def test_resolve():
    cfg = {
        "a": "aa",
        "b": "{ref:a}",
        "c": "{ref:b}",
        "d": "{ref:xxx}",
    }

    model = MyClass(cfg)
    ref = RefPlaceholder("a")
    assert ref.resolve(model, None) == "aa"

    ref = RefPlaceholder("b")
    assert ref.resolve(model, None) == "aa"

    ref = RefPlaceholder("c")
    assert ref.resolve(model, None) == "aa"

    ref = RefPlaceholder("d")
    with pytest.raises(ConfigException):
        ref.resolve(model, None)

    ref = RefPlaceholder("xxx")
    with pytest.raises(ConfigException):
        ref.resolve(model, None)


def test_global_ref():
    cfg = {
        "a": "aa",
        "b": "{global:a}",
        "c": "{global:b}",
        "d": "{global:xxx}",
    }

    model = MyClass(cfg)
    ref = GlobalRefPlaceholder("a")
    assert ref.resolve(model, None) == "aa"

    ref = GlobalRefPlaceholder("b")
    assert ref.resolve(model, None) == "aa"

    ref = GlobalRefPlaceholder("c")
    assert ref.resolve(model, None) == "aa"

    ref = GlobalRefPlaceholder("d")
    with pytest.raises(ConfigException):
        ref.resolve(model, None)

    ref = GlobalRefPlaceholder("xxx")
    with pytest.raises(ConfigException):
        ref.resolve(model, None)


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

    model = MyClass(cfg)
    model.register_placeholder_handler("bespoke", MyBespokePlaceholder)
    ref = RefPlaceholder("a")
    assert ref.resolve(model, None) == "it's me"


def test_mandatory_value():
    cfg = {
        "a": "???",
        "b": "{ref:a}",
    }

    model = MyClass(cfg)
    ref = RefPlaceholder("a")
    with pytest.raises(ConfigException):
        assert ref.resolve(model, None)

    ref = RefPlaceholder("b")
    with pytest.raises(ConfigException):
        assert ref.resolve(model, None)


def test_detect_recursion():
    cfg = {
        "a": "{ref:b}",
        "b": "{ref:c}",
        "c": "{ref:a}",
    }

    model = MyClass(cfg)
    ref = RefPlaceholder("a")
    with pytest.raises(ConfigException):
        assert ref.resolve(model, None)

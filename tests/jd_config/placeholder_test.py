#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C

import logging
from dataclasses import dataclass

import pytest

from jd_config import (
    ConfigException,
    EnvPlaceholder,
    GlobalRefPlaceholder,
    ImportPlaceholder,
    Placeholder,
    RefPlaceholder,
    ResolverMixin,
)
from jd_config.deep_getter import DeepGetter, GetterContext

logger = logging.getLogger(__name__)

# Notes:
# show logs: pytest --log-cli-level=DEBUG


class MyConfig(ResolverMixin, DeepGetter):
    def __init__(self) -> None:
        DeepGetter.__init__(self)
        ResolverMixin.__init__(self)


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
    assert obj.default_val is None

    # Filename is missing
    with pytest.raises(Exception):
        EnvPlaceholder(env_var="")

    monkeypatch.setenv("ENV", "this is a test")

    resolver = ResolverMixin()
    env = EnvPlaceholder("ENV")
    assert env.resolve(resolver) == "this is a test"


def test_resolve():
    cfg = {
        "a": "aa",
        "b": "{ref:a}",
        "c": "{ref:b}",
        "d": "{ref:xxx}",
    }

    resolver = MyConfig()
    ctx = GetterContext(cfg)
    ref = RefPlaceholder("a")
    assert ref.resolve(resolver, ctx) == "aa"

    ref = RefPlaceholder("b")
    ctx = GetterContext(cfg)
    assert ref.resolve(resolver, ctx) == "aa"

    ref = RefPlaceholder("c")
    ctx = GetterContext(cfg)
    assert ref.resolve(resolver, ctx) == "aa"

    ref = RefPlaceholder("d")
    ctx = GetterContext(cfg)
    with pytest.raises(ConfigException):
        ref.resolve(resolver, ctx)

    ref = RefPlaceholder("xxx")
    ctx = GetterContext(cfg)
    with pytest.raises(ConfigException):
        ref.resolve(resolver, ctx)


def test_global_ref():
    cfg = {
        "a": "aa",
        "b": "{global:a}",
        "c": "{global:b}",
        "d": "{global:xxx}",
    }

    resolver = MyConfig()
    ctx = GetterContext(cfg)
    ref = GlobalRefPlaceholder("a")
    assert ref.resolve(resolver, ctx) == "aa"

    ref = GlobalRefPlaceholder("b")
    ctx = GetterContext(cfg)
    assert ref.resolve(resolver, ctx) == "aa"

    ref = GlobalRefPlaceholder("c")
    ctx = GetterContext(cfg)
    assert ref.resolve(resolver, ctx) == "aa"

    ref = GlobalRefPlaceholder("d")
    ctx = GetterContext(cfg)
    with pytest.raises(ConfigException):
        ref.resolve(resolver, ctx)

    ref = GlobalRefPlaceholder("xxx")
    ctx = GetterContext(cfg)
    with pytest.raises(ConfigException):
        ref.resolve(resolver, ctx)


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

    resolver = MyConfig()
    ctx = GetterContext(cfg)
    resolver.register_placeholder_handler("bespoke", MyBespokePlaceholder)
    ref = RefPlaceholder("a")
    assert ref.resolve(resolver, ctx) == "it's me"


def test_mandatory_value():
    cfg = {
        "a": "???",
        "b": "{ref:a}",
    }

    resolver = MyConfig()
    ctx = GetterContext(cfg)
    ref = RefPlaceholder("a")
    with pytest.raises(ConfigException):
        assert ref.resolve(resolver, ctx)

    ref = RefPlaceholder("b")
    ctx = GetterContext(cfg)
    with pytest.raises(ConfigException):
        assert ref.resolve(resolver, ctx)


def test_detect_recursion():
    cfg = {
        "a": "{ref:b}",
        "b": "{ref:c}",
        "c": "{ref:a}",
    }

    resolver = MyConfig()
    ctx = GetterContext(cfg)
    ref = RefPlaceholder("a")
    with pytest.raises(RecursionError):
        assert ref.resolve(resolver, ctx)

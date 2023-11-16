#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C

import logging
from dataclasses import dataclass

import pytest

from jd_config import (
    DEFAULT,
    ConfigException,
    DeepGetter,
    EnvPlaceholder,
    GetterContext,
    GlobalRefPlaceholder,
    ImportPlaceholder,
    Placeholder,
    RefPlaceholder,
    ResolverMixin,
)

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

    resolver = ResolverMixin()
    ctx = GetterContext({})
    ctx.getter_pipeline = (resolver.cb_get, DeepGetter.cb_get)

    env = EnvPlaceholder("ENV")
    assert env.resolve(ctx, None) == "this is a test"


def test_resolve():
    cfg = {
        "a": "aa",
        "b": "{ref:a}",
        "c": "{ref:b}",
        "d": "{ref:xxx}",
    }

    resolver = ResolverMixin()
    ctx = GetterContext(cfg)
    ctx.getter_pipeline = (resolver.cb_get, DeepGetter.cb_get)

    ref = RefPlaceholder("a")
    assert ref.resolve(ctx, None) == "aa"

    ref = RefPlaceholder("b")
    ctx = GetterContext(cfg)
    ctx.getter_pipeline = (resolver.cb_get, DeepGetter.cb_get)
    assert ref.resolve(ctx, None) == "aa"

    ref = RefPlaceholder("c")
    ctx = GetterContext(cfg)
    ctx.getter_pipeline = (resolver.cb_get, DeepGetter.cb_get)
    assert ref.resolve(ctx, None) == "aa"

    ref = RefPlaceholder("d")
    ctx = GetterContext(cfg)
    ctx.getter_pipeline = (resolver.cb_get, DeepGetter.cb_get)
    with pytest.raises(ConfigException):
        ref.resolve(ctx, None)

    ref = RefPlaceholder("xxx")
    ctx = GetterContext(cfg)
    ctx.getter_pipeline = (resolver.cb_get, DeepGetter.cb_get)
    with pytest.raises(ConfigException):
        ref.resolve(ctx, None)


def test_global_ref():
    cfg = {
        "a": "aa",
        "b": "{global:a}",
        "c": "{global:b}",
        "d": "{global:xxx}",
    }

    resolver = ResolverMixin()
    ctx = GetterContext(cfg)
    ctx.getter_pipeline = (resolver.cb_get, DeepGetter.cb_get)
    ref = GlobalRefPlaceholder("a")
    assert ref.resolve(ctx, None) == "aa"

    ref = GlobalRefPlaceholder("b")
    ctx = GetterContext(cfg)
    ctx.getter_pipeline = (resolver.cb_get, DeepGetter.cb_get)
    assert ref.resolve(ctx, None) == "aa"

    ref = GlobalRefPlaceholder("c")
    ctx = GetterContext(cfg)
    ctx.getter_pipeline = (resolver.cb_get, DeepGetter.cb_get)
    assert ref.resolve(ctx, None) == "aa"

    ref = GlobalRefPlaceholder("d")
    ctx = GetterContext(cfg)
    ctx.getter_pipeline = (resolver.cb_get, DeepGetter.cb_get)
    with pytest.raises(ConfigException):
        ref.resolve(ctx, None)

    ref = GlobalRefPlaceholder("xxx")
    ctx = GetterContext(cfg)
    ctx.getter_pipeline = (resolver.cb_get, DeepGetter.cb_get)
    with pytest.raises(ConfigException):
        ref.resolve(ctx, None)


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

    resolver = ResolverMixin()
    resolver.register_placeholder_handler("bespoke", MyBespokePlaceholder)
    ctx = GetterContext(cfg)
    ctx.getter_pipeline = (resolver.cb_get, DeepGetter.cb_get)
    ref = RefPlaceholder("a")
    assert ref.resolve(ctx, None) == "it's me"


def test_mandatory_value():
    cfg = {
        "a": "???",
        "b": "{ref:a}",
    }

    resolver = ResolverMixin()
    ctx = GetterContext(cfg)
    ctx.getter_pipeline = (resolver.cb_get, DeepGetter.cb_get)
    ref = RefPlaceholder("a")
    with pytest.raises(ConfigException):
        assert ref.resolve(ctx, None)

    ref = RefPlaceholder("b")
    ctx = GetterContext(cfg)
    ctx.getter_pipeline = (resolver.cb_get, DeepGetter.cb_get)
    with pytest.raises(ConfigException):
        assert ref.resolve(ctx, None)


def test_detect_recursion():
    cfg = {
        "a": "{ref:b}",
        "b": "{ref:c}",
        "c": "{ref:a}",
    }

    resolver = ResolverMixin()
    ctx = GetterContext(cfg)
    ctx.getter_pipeline = (resolver.cb_get, DeepGetter.cb_get)
    ref = RefPlaceholder("a")
    with pytest.raises(ConfigException):
        assert ref.resolve(ctx, None)

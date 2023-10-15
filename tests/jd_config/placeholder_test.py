#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C

import logging
from dataclasses import dataclass

import pytest

from jd_config import (
    ConfigException,
    ConfigResolveMixin,
    EnvPlaceholder,
    GlobalRefPlaceholder,
    ImportPlaceholder,
    Placeholder,
    RefPlaceholder,
)
from jd_config.deep_getter_base import DeepGetter
from jd_config.resolver_mixin import ResolverMixin

logger = logging.getLogger(__name__)

# Notes:
# show logs: pytest --log-cli-level=DEBUG


class MyConfig(ConfigResolveMixin, DeepGetter):
    def __init__(self) -> None:
        DeepGetter.__init__(self)
        ConfigResolveMixin.__init__(self)


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
    ref = RefPlaceholder("a")
    assert ref.resolve(resolver, cfg) == "aa"

    ref = RefPlaceholder("b")
    assert ref.resolve(resolver, cfg) == "aa"

    ref = RefPlaceholder("c")
    assert ref.resolve(resolver, cfg) == "aa"

    with pytest.raises(ConfigException):
        ref = RefPlaceholder("d")
        ref.resolve(resolver, cfg)

    with pytest.raises(ConfigException):
        ref = RefPlaceholder("xxx")
        ref.resolve(resolver, cfg)


def test_global_ref():
    cfg = {
        "a": "aa",
        "b": "{global:a}",
        "c": "{global:b}",
        "d": "{global:xxx}",
    }

    resolver = MyConfig()
    ref = GlobalRefPlaceholder("a")
    assert ref.resolve(resolver, cfg) == "aa"

    ref = GlobalRefPlaceholder("b")
    assert ref.resolve(resolver, cfg) == "aa"

    ref = GlobalRefPlaceholder("c")
    assert ref.resolve(resolver, cfg) == "aa"

    with pytest.raises(ConfigException):
        ref = GlobalRefPlaceholder("d")
        ref.resolve(resolver, cfg)

    with pytest.raises(ConfigException):
        ref = GlobalRefPlaceholder("xxx")
        ref.resolve(resolver, cfg)


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
    resolver.register_placeholder_handler("bespoke", MyBespokePlaceholder)
    ref = RefPlaceholder("a")
    assert ref.resolve(resolver, cfg) == "it's me"


def test_mandatory_value():
    cfg = {
        "a": "???",
        "b": "{ref:a}",
    }

    resolver = MyConfig()
    ref = RefPlaceholder("a")
    with pytest.raises(ConfigException):
        assert ref.resolve(resolver, cfg)

    ref = RefPlaceholder("b")
    with pytest.raises(ConfigException):
        assert ref.resolve(resolver, cfg)


def test_detect_recursion():
    cfg = {
        "a": "{ref:b}",
        "b": "{ref:c}",
        "c": "{ref:a}",
    }

    resolver = MyConfig()
    ref = RefPlaceholder("a")
    with pytest.raises(RecursionError):
        assert ref.resolve(resolver, cfg)

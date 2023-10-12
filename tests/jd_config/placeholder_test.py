#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C

from dataclasses import dataclass
import logging
import pytest
from jd_config import RefPlaceholder, ImportPlaceholder, EnvPlaceholder
from jd_config import GlobalRefPlaceholder
from jd_config import ConfigException, Placeholder, PlaceholderException
from jd_config import ConfigResolveMixin

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

    resolver = ConfigResolveMixin(data=cfg, path=())
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

    resolver = ConfigResolveMixin(data=cfg, path=())
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

    resolver = ConfigResolveMixin(data=cfg, path=())
    resolver.register_placeholder_handler("bespoke", MyBespokePlaceholder)
    ref = RefPlaceholder("a")
    assert ref.resolve(resolver, cfg) == "it's me"


def test_mandatory_value():
    cfg = {
        "a": "???",
        "b": "{ref:a}",
    }

    resolver = ConfigResolveMixin(data=cfg, path=())
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

    resolver = ConfigResolveMixin(data=cfg, path=())
    ref = RefPlaceholder("a")
    with pytest.raises(RecursionError):
        assert ref.resolve(resolver, cfg)

#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C

import logging
from typing import Mapping, Sequence

from jd_config.base_model import BaseModel

logger = logging.getLogger(__name__)

# Notes:
# show logs: pytest --log-cli-level=DEBUG


def test_get_from_dict():
    cfg = {
        "a": "aa",
        "b": {"ba": 11, "bb": {"bba": 22, "bbb": 33}},
        "c": [1, 2, 3, {"c4a": 44, "c4b": 55}],
    }

    data = BaseModel(cfg)
    assert data.get("") == cfg
    assert data.get("a") == "aa"
    assert data.get("b") == cfg["b"]
    assert data.get("b.ba") == 11
    assert data.get("b.bb") == {"bba": 22, "bbb": 33}
    assert data.get("b.bb.bba") == 22
    assert data.get("b.bb.bbb") == 33
    assert data.get("c") == cfg["c"]
    assert data.get("c[0]") == 1
    assert data.get("c[1]") == 2
    assert data.get("c[2]") == 3
    assert data.get("c[3]") == {"c4a": 44, "c4b": 55}
    assert data.get("c[3].c4a") == 44
    assert data.get("c[3].c4b") == 55


def test_isinstance():
    data = BaseModel({"a": "aa"})
    assert data.is_mapping() is True
    assert data.is_sequence() is False
    assert data.__isinstance__(Mapping) is True
    assert data.__isinstance__(Sequence) is False
    # assert isinstance(data, Mapping) is True
    # assert isinstance(data, Sequence) is False

    data = BaseModel([1])
    assert data.is_mapping() is False
    assert data.is_sequence() is True
    assert data.__isinstance__(Mapping) is False
    assert data.__isinstance__(Sequence) is True
    # assert isinstance(data, Mapping) is False
    # assert isinstance(data, Sequence) is True


def test_list_root():
    cfg = [1, 2, 3, {"c4a": 44, "c4b": 55}]

    # Test to give it a list as root element
    data = BaseModel(cfg)
    assert data.get("[0]") == 1
    assert data.get("[1]") == 2
    assert data.get("[2]") == 3
    assert data.get("[3]") == {"c4a": 44, "c4b": 55}
    assert data.get("[3].c4a") == 44
    assert data.get("[3].c4b") == 55


def test_get_from_dict_getattr():
    cfg = {
        "a": "aa",
        "b": {"ba": 11, "bb": {"bba": 22, "bbb": 33}},
        "c": [1, 2, 3, {"c4a": 44, "c4b": 55}],
    }

    data = BaseModel(cfg)
    assert data["a"] == "aa"
    assert data["b.bb.bba"] == 22
    assert data["b.bb.bbb"] == 33
    assert data["c[0]"] == 1
    assert data["c[3].c4a"] == 44


def test_list_root_getattr():
    cfg = [1, 2, 3, {"c4a": 44, "c4b": 55}]

    # Test to give it a list as root element
    data = BaseModel(cfg)
    assert data["[0]"] == 1
    assert data[0] == 1
    assert data["[1]"] == 2
    assert data["[3].c4b"] == 55
    assert data[(3, "c4a")] == 44


def test_get_default():
    cfg = {
        "a": "aa",
        "b": {"ba": 11, "bb": {"bba": 22, "bbb": 33}},
        "c": [1, 2, 3, {"c4a": 44, "c4b": 55}],
    }

    data = BaseModel(cfg)
    assert data.get("does_not_exist", default="me") == "me"
    assert data.get("b.bb.does_not_exist", default="me") == "me"
    assert data.get("c[3].does_not_exist", default="me") == "me"
    assert data.get("c[99].c4b", 123) == 123


def test_on_missing():
    cfg = {
        "a": "aa",
        "b": {"ba": 11, "bb": {"bba": 22, "bbb": 33}},
        "c": [1, 2, 3, {"c4a": 44, "c4b": 55}],
    }

    data = BaseModel(cfg)
    assert data.get("does_not_exist", on_missing=lambda *_, **__: "me") == "me"
    assert data.get("b.bb.does_not_exist", on_missing=lambda *_, **__: "me") == "me"
    assert data.get("c[3].does_not_exist", on_missing=lambda *_, **__: "me") == "me"


def test_iter():
    cfg = {
        "a": "aa",
        "b": {"ba": 11, "bb": {"bba": 22, "bbb": 33}},
        "c": [1, 2, 3, {"c4a": 44, "c4b": 55}],
    }

    data = BaseModel(cfg)
    rtn = list((k, v) for k, v in data.items())
    assert rtn == [
        ("a", "aa"),
        ("b", {"ba": 11, "bb": {"bba": 22, "bbb": 33}}),
        ("c", [1, 2, 3, {"c4a": 44, "c4b": 55}]),
    ]

    rtn = list((k, v) for k, v in data.get("c").items())
    assert rtn == [
        (0, 1),
        (1, 2),
        (2, 3),
        (3, {"c4a": 44, "c4b": 55}),
    ]


def test_relativ():
    cfg = {
        "a": "aa",
        "b": {"ba": 11, "bb": {"bba": 22, "bbb": 33}},
        "c": [1, 2, 3, {"c4a": 44, "c4b": 55}],
    }

    data = BaseModel(cfg)
    data = data.get("b")
    assert data.get("ba") == 11
    assert data.get("./ba") == 11
    assert data.get("../a") == "aa"

    # Must also work with leaf ("a") followed by ".."
    data = BaseModel(cfg)
    assert data.get("a/../b/ba") == 11

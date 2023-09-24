#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C

import logging
from jd_config import convert, convert_bool
import pytest

logger = logging.getLogger(__name__)

# Notes:
# show logs: pytest --log-cli-level=DEBUG

def test_convert_bool():

    assert convert_bool("false") == False
    assert convert_bool("False") == False
    assert convert_bool("faLsE") == False
    assert convert_bool("no") == False
    assert convert_bool("NO") == False
    assert convert_bool("0") == False
    assert convert_bool("true") == True
    assert convert_bool("TrUE") == True
    assert convert_bool("yes") == True
    assert convert_bool("1") == True

    with pytest.raises(KeyError):
        convert_bool("2")

    with pytest.raises(KeyError):
        convert_bool("10")

    with pytest.raises(KeyError):
        convert_bool("00")

    with pytest.raises(KeyError):
        convert_bool("truex")

def test_convert():

    assert convert("0") == 0
    assert convert("1") == 1
    assert convert("2") == 2
    assert convert("-1") == -1
    assert convert("1.2") == 1.2
    assert convert("0.3") == 0.3
    assert convert("text") == "text"
    assert convert("0.3.4") == "0.3.4"
    assert convert("true") == True
    assert convert("no") == False
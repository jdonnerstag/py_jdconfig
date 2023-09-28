#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""Little helpers to convert string into int, float and bool
"""

import logging
from typing import Any


__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


class StringConverterMixin:
    """Mixin adding support to evaluate string into int, float, bool or strring.

    Dependencies: None
    """

    @classmethod
    def convert(cls, strval: Any) -> int | float | str | bool:
        """Convert a string into int, float or bool of possible, else
        return the string value.

        :param strval: Input yaml string value
        """
        if isinstance(strval, str):
            # Note: the sequence is very important !!
            possible = [int, float, cls.convert_bool, str]
            for func in possible:
                try:
                    return func(strval)
                except (ValueError, KeyError):
                    continue

        return strval

    @classmethod
    def convert_bool(cls, strval: str) -> bool:
        """Convert a string into a bool, if possible. Else throw an Exception.

        :param strval: Input yaml string value
        """
        bool_vals = {
            "false": False,
            "no": False,
            "0": False,
            "true": True,
            "yes": True,
            "1": True,
        }

        if len(strval) > 5:
            raise ValueError(strval)

        text = strval.lower()
        return bool_vals[text]

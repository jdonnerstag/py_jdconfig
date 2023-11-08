#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
"""

import logging
from typing import Any, Callable, Optional
from weakref import WeakKeyDictionary
from .utils import DEFAULT

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


class Field:
    def __init__(
        self,
        name: str = None,
        *,
        default: Any = DEFAULT,
        default_factory: Optional[Callable] = None,
    ) -> None:
        self.input_name: str | None = name
        self.model_name: str | None = None
        self.def_value: Any | None = default
        self.default_factory = default_factory

        # Dict key is the BaseModel, and if that object gets garbage collected,
        # the respective dict entry can be removed. Not need to keep it.
        # Fields are assigned to class variables in the BaseModel. Which means,
        # they are only initialized ones per BaseModel class and not ones per
        # BaseModel instance.
        self.values = WeakKeyDictionary()

    def __set_name__(self, owner, name):
        self.model_name = name

        if self.input_name is None:
            self.input_name = name

    def __get__(self, obj, objtype=None):
        value = self.values.get(obj, self.def_value)
        if value != DEFAULT:
            return value

        if callable(self.default_factory):
            # Types, e.g. dict, list, etc. are callable
            return self.default_factory()

        raise AttributeError(f"No input value for '{self.model_name}'")

    def __set__(self, obj, value):
        self.values[obj] = value

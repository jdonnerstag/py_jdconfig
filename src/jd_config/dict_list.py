#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
In the context of Configs and yaml files, dict- and list-like containers
play an important role. DictList harmonizes access to these dicts and lists,
and thus simplies the code accessing configs.
"""

import logging
from typing import Any, Mapping, Iterator

from .utils import NonStrSequence, DEFAULT, ContainerType


__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


class DictList(Mapping, NonStrSequence):
    """Harmonize access to configs managed in dict- and/or list-like
    containers.
    """

    def __init__(self, obj: ContainerType) -> None:
        assert isinstance(obj, (Mapping, NonStrSequence))
        self.obj = obj

    def _new_item(self, _key, obj):
        return DictList(obj)

    def __getitem__(self, key: str | int) -> Any:
        try:
            rtn = self.obj[key]
            if isinstance(rtn, (Mapping, NonStrSequence)):
                return self._new_item(key, rtn)

            return rtn
        except (KeyError, IndexError):
            if not hasattr(self, "__missing__"):
                raise

            # pylint: disable=no-member
            new_value = self.__missing__(key)
            self.__setitem__(key, new_value)
            return new_value

    def __setitem__(self, key: str | int, item: Any) -> None:
        self.obj[key] = item

    def __len__(self) -> int:
        return len(self.obj)

    def __iter__(self) -> Iterator:
        raise NotImplementedError("Please use .items(), .keys() or .values() instead")

    def items(self) -> Iterator:
        if isinstance(self.obj, Mapping):
            return self.obj.items()

        return enumerate(self.obj)

    def keys(self) -> Iterator:
        if isinstance(self.obj, Mapping):
            return self.obj.keys()

        return range(len(self.obj))

    def values(self) -> Iterator:
        if isinstance(self.obj, Mapping):
            return self.obj.values()

        return self.obj

    def __contains__(self, key: str | int) -> bool:
        if isinstance(self.obj, Mapping):
            return key in self.obj

        return 0 <= key < len(self.obj)

    def get(self, key: str | int, default: Any = DEFAULT) -> Any:
        try:
            return self[key]
        except (KeyError, IndexError):
            if default != DEFAULT:
                return default

            raise

    def __eq__(self, other):
        if isinstance(other, DictList):
            other = other.obj

        return self.obj.__eq__(other)

    def __repr__(self) -> str:
        return self.obj.__repr__()

    def __str__(self) -> str:
        return self.obj.__str__()

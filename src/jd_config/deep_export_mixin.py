#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Mixin to export deep config data
"""

import logging
from typing import Optional

import yaml

from .base_model import BaseModel
from .config_path import PathType
from .utils import ContainerType

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


class DeepExportMixin:
    """A mixin to export configs into dict or yaml structures.

    Dependencies:
    - self.data: the config object structure
    - self.resolve(): a method to lazily resolve placeholders
    - self.get(): acces a (deep) config node
    """

    def to_dict(self, path: Optional[PathType] = None, **kvargs) -> dict | list:
        """Walk the config items with an optional starting point, and create a
        dict from it.
        """
        if path:
            return self.get(path).to_dict(**kvargs)

        if self.is_mapping():
            return self._to_dict_dict(**kvargs)
        if self.is_sequence():
            return self._to_dict_list(**kvargs)

        raise AttributeError(f"Expected a ContainerType: '{self.data}'")

    def _to_dict_dict(self, **kvargs) -> dict:
        rtn = {}
        for k, v in self.items():
            # Make sure we resolve or whatever else is necessary
            v = self.get(k, **kvargs)
            if isinstance(v, ContainerType):
                child = self.clone(v, k)
                rtn[k] = child.to_dict(**kvargs)
            elif isinstance(v, BaseModel):
                rtn[k] = v.to_dict(**kvargs)
            else:
                rtn[k] = v

        return rtn

    def _to_dict_list(self, **kvargs) -> list:
        rtn = []
        for i, v in self.items():
            # Make sure we resolve or whatever else is necessary
            v = self.get(i, **kvargs)
            if isinstance(v, ContainerType):
                child = self.clone(v, i)
                rtn.append(child.to_dict(**kvargs))
            elif isinstance(v, BaseModel):
                rtn.append(v.to_dict(**kvargs))
            else:
                rtn.append(v)

        return rtn

    def to_yaml(self, path: Optional[PathType] = None, stream=None, **kvargs):
        """Convert the configs (or part of it), into a yaml document"""

        data = self.to_dict(path, **kvargs)
        return yaml.dump(data, stream, **kvargs)

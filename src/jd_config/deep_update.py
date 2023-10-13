#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
"""

import logging
from typing import Mapping, Optional, Sequence, TYPE_CHECKING

from .utils import NonStrSequence, ConfigException
from .objwalk import (
    ObjectWalker,
    NodeEvent,
    NewMappingEvent,
    NewSequenceEvent,
    DropContainerEvent,
)

if TYPE_CHECKING:
    from jd_config.deep_dict import DeepDict

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


class DeepUpdateMixin:
    """ """

    def deep_update(self, updates: Optional[Mapping]) -> "DeepDict":
        """Deep update the 'obj' with only the leafs from 'updates'. Create
        missing paths.

        :param obj: The dict that will be updated
        :param updates: The dict providing the values to update
        :param create_missing: If true, create any missing level.
        :return: the updated 'obj'
        """

        if not updates:
            return self.obj

        for event in ObjectWalker.objwalk(updates, nodes_only=True):
            self.set(event.path, event.value, create_missing=True, replace_path=True)

        return self

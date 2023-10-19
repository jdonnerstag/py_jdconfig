#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Deep update a dict with values from another deep structure.

The functionality is e.g. use when overlaying environment specific
configuration over the default one. E.g. assume default is the
production configuration and for 'dev' you want to apply some
changes to the 'prod' one.
"""

import logging
from typing import TYPE_CHECKING, Mapping, Optional

from .objwalk import objwalk

if TYPE_CHECKING:
    from jd_config.deep_dict import DeepDict

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


# pylint: disable=too-few-public-methods
class DeepUpdateMixin:
    """Deep update a dict with values from another deep structure.

    The functionality is e.g. use when overlaying environment specific
    configuration over the default one. E.g. assume default is the
    production configuration and for 'dev' you want to apply some
    changes to the 'prod' one.
    """

    def deep_update(self, updates: Optional[Mapping]) -> "DeepDict":
        """Deep update the 'obj' with only the leafs from 'updates'. Create
        missing paths.

        :param obj: The dict that will be updated
        :param updates: The dict providing the values to update
        :return: the updated 'obj'
        """

        if not updates:
            return self.obj

        for event in objwalk(updates, nodes_only=True):
            self.set(event.path, event.value, create_missing=True, replace_path=True)

        return self

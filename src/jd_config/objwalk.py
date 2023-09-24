#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
A generic function to walk any Mapping- and Sequence- like objects.
"""

import logging
from typing import Any, Mapping, Optional, Sequence, Set, Tuple, Iterator

__parent__name__ = __name__.rpartition('.')[0]
logger = logging.getLogger(__parent__name__)


def objwalk(obj: Any, path: Tuple=(), memo: Optional[Set] = None) -> Iterator[Tuple[Tuple, Any]]:
    """A generic function to walk any Mapping- and Sequence- like objects.

    Once loaded into memory, Yaml and Json files, are often implemented with
    nested dict- and list-like object structures.

    'objwalk' walks the structure depth first. Only leaf-nodes are yielded.

    :param obj: The root container to start walking.
    :param path: internal use only.
    :param memo: internal use only.
    :return: 'objwalk' is a generator function, yielding the elements path and obj.
    """

    if memo is None:
        memo = set()

    if isinstance(obj, Mapping):
        if id(obj) not in memo:
            memo.add(id(obj))
            for key, value in obj.items():
                for child in objwalk(value, path + (key,), memo):
                    yield child

    elif isinstance(obj, (Sequence, Set)) and not isinstance(obj, str):
        if id(obj) not in memo:
            memo.add(id(obj))
            for index, value in enumerate(obj):
                for child in objwalk(value, path + (index,), memo):
                    yield child

    else:
        yield path, obj

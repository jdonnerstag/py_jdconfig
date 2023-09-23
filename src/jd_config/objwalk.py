#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import logging
from typing import Any, Mapping, Optional, Sequence, Set, Tuple

logger = logging.getLogger(__name__)


def objwalk(obj: Any, path:Tuple=(), memo: Optional[Set]=None) -> Tuple[Tuple, Any]:
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

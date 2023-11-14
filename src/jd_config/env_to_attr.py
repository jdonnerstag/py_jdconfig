#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""A little util to load ENV vars into class attributes"""

import dataclasses
from typing import Any, Mapping, Union, get_type_hints

from jd_config.utils import ConfigException


def _parse_bool(val: Union[str, bool]) -> bool:
    return val if isinstance(val, bool) else val.lower() in ["true", "yes", "1"]


def load_env_into_attr(obj: Any, env: Mapping) -> Any:
    """
    Map environment variables to class fields according to these rules:
      - Field won't be parsed unless it has a type annotation
      - Field will be skipped if not in all caps
      - Class field and environment variable name are the same

    E.g.
    '''
    @dataclass
    class AppConfig:
        DEBUG: bool = False
        ENV: str = 'production'
        API_KEY: str
        HOSTNAME: str
        PORT: int
    '''

    app = load_env_into_attr(AppConfig, os.environ)
    """
    type_hints = get_type_hints(obj)

    attrs = {}
    for field in obj.__annotations__:
        if not field.isupper():
            continue

        # Raise exception if required field not supplied
        default_value = getattr(obj, field, None)
        if default_value is None and env.get(field) is None:
            raise AttributeError(f"Field is required: '{field}'")

        # Cast env var value to expected type and raise AppConfigError on failure

        try:
            var_type = type_hints[field]
            value = env.get(field, default_value)
            if var_type is bool:
                value = _parse_bool(value)
            else:
                value = var_type(value)

            attrs[field] = value
        except ValueError as exc:
            raise ConfigException(
                f"Unable to cast value of '{env[field]}' to type '{var_type}' for '{field}' field"
            ) from exc

    if dataclasses.is_dataclass(obj):
        return obj(**attrs)

    if isinstance(obj, type):
        obj = obj()  # Must have default constructor

    for k, v in attrs.items():
        setattr(obj, k, v)

    return obj

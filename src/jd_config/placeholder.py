#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""Manage everything related to placeholders, such as
```
  db_engine: '{ref: db.engine, innodb}'
```

Placeholders can only occur in yaml values. They are not allowed in keys.
And it must be a yaml *string* value, surrounded by quotes.
"""

import logging
from dataclasses import dataclass
from typing import Any, Iterator, Union, List
from .config_getter import ConfigException
from .convert import convert


__parent__name__ = __name__.rpartition('.')[0]
logger = logging.getLogger(__parent__name__)



ValueType = Union[int, float, bool, str, 'Placeholder']

class CompoundValue(list):
    """A Yaml value that consists of multiple parts.

    E.g. Upon reading the yaml file, a value such as "test-{ref:database}-url"
    will be preprocessed and split into 3 parts: "test-", <Placeholder>, and "-url".
    All part together make CompoundValue, with few helper. E.g. resolve
    the placeholders and determine the actual value.
    """

    def __init__(self, values: Iterator[ValueType]) -> None:
        super().__init__(list(values))

    def is_import(self) -> bool:
        """Determine if one the parts is a '{import:..}' placeholder
        """

        for elem in self:
            if isinstance(elem, ImportPlaceholder):
                assert elem.name == "import"    # Else, it is a bug

                # Import Placeholders must be standalone.
                if len(self) != 1:
                    raise ConfigException("Invalid '{import: ...}', ${elem}")

                return True

        return False


@dataclass
class Placeholder:
    """A common base class for all Placeholders
    """
    name: str
    args: List[ValueType]


@dataclass
class ImportPlaceholder(Placeholder):
    """Import Placeholder: '{import: <file>[, <replace=False>]}'
    """

    @property
    def file(self) -> str:
        """The 1st argument: the yaml file to import"""
        return self.args[0]

    @property
    def env(self) -> str | None:
        """The 2nd argument: the environment, e.g. dev, test, prod"""

        if len(self.args) > 1:
            return self.args[1]
        return None

    @property
    def replace(self) -> bool:
        """The 3rd argument: False - replace yaml value; True - merge with parent container
        """

        if len(self.args) > 2:
            return bool(self.args[2])
        return False


@dataclass
class RefPlaceholder(Placeholder):
    """Reference Placeholder: '{ref: <path>[, <default>]}'
    """

    @property
    def path(self) -> str:
        """The 1st argument: path to the reference element"""
        return self.args[0]

    @property
    def default(self) -> str | None:
        """The 2nd argument: A default value'"""

        if len(self.args) > 1:
            return self.args[1]
        return None


class ValueReaderException(ConfigException):
    """Denote an Exception that occured while parsing a yaml value (wiht placeholder)"""

class ValueReader:
    """Parse a yaml value
    """

    @classmethod
    def parse(cls, strval: str, *, sep: str = ",") -> Iterator[ValueType]:
        """Parse a yaml value and yield the various parts.

        :param strval: Input yaml string value
        :param sep: argument separator. Default: ','
        :return: Generator yielding individual parts of the yaml string value
        """

        stack: List[Placeholder] = []
        _iter = cls.tokenize(strval, sep)
        try:
            while text := next(_iter, None):
                if text == "{":
                    name = next(_iter)
                    colon = next(_iter)
                    assert colon == ":"
                    placeholder = Placeholder(name, [])
                    if name == "import":
                        placeholder.__class__ = ImportPlaceholder
                    elif name == "ref":
                        placeholder.__class__ = RefPlaceholder
                    stack.append(placeholder)
                elif text == "}" and stack:
                    placeholder = stack.pop()
                    if not stack:
                        yield placeholder
                    else:
                        stack[-1].args.append(placeholder)
                elif isinstance(text, str) and text.find("{") != -1:
                    values = list(ValueReader().parse(text))
                    values = [cls.convert(x) for x in values]
                    value = CompoundValue(values)
                    if not stack:
                        yield value
                    else:
                        stack[-1].args.append(value)

                else:
                    value = cls.convert(text)
                    if not stack:
                        yield value
                    else:
                        stack[-1].args.append(value)

        except StopIteration as exc:
            raise ValueReaderException(
                f"Failed to parse yaml value with placeholder: '${strval}'") from exc

    @classmethod
    def tokenize(cls, strval: str, sep: str = ",") -> Iterator[str]:
        """Tokenize the yaml string value

        :param strval: Input yaml string value
        :param sep: argument separator. Default: ','
        :return: Generator yielding individual string tokens
        """

        start = 0
        i = 0
        while i < len(strval):
            c = strval[i]
            if c == "\\":
                i += 1
            elif c in ['"', "'"]:
                i = cls.find_closing_quote(strval, i)
                value = strval[start + 2 : i]
                yield value
                start = i + 1
            elif c in [sep, "{", "}", ":"]:
                value = strval[start : i].strip()
                if value:
                    yield value
                start = i + 1

                if c is not sep:
                    yield c

            i += 1

        value = strval[start : ].strip()
        if value:
            yield value

    @classmethod
    def find_closing_quote(cls, strval: str, start: int) -> int:
        """Given a start position, determine the end of a quote.

        The first character determine the quote, e.g. "'", '"'

        :param strval: Input yaml string value
        :param start: position where the quote starts
        :return: position where the quote ends

        """

        quote_char = strval[start]
        i = start + 1
        while i < len(strval):
            char = strval[i]
            if char == "\\":
                i += 1
            elif char == quote_char:
                return i

            i += 1

        return i - 1


    @classmethod
    def convert(cls, strval: Any) -> int | float | str | bool:
        """Convert a string into int, float or bool of possible, else
        return the string value.

        :param strval: Input yaml string value
        """
        return convert(strval)

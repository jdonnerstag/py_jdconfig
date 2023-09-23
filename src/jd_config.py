
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, Optional, Sequence, Set, Tuple, Union, List
import yaml


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

@dataclass
class YamlObj:
    line: int
    column: int
    file: str
    value: Any

@dataclass
class YamlContainer:
    count: int

    def incr(self) -> int:
        self.count += 1
        return self.count

@dataclass
class YamlMapping(YamlContainer):
    pass

@dataclass
class YamlSequence(YamlContainer):
    pass

DEFAULT = object()

class ConfigGetter:

    @classmethod
    def walk(cls, _data: Mapping, path: str | int | Iterable, sep: str=".") -> Tuple[Any, Any]:

        # TODO: Support
        # "a.b.c", "a[1].b", "a/b/c", "[a][b][c]", ["a", "b", "c"], ("a", "b", "c",), ["a", "b.c"]
        if isinstance(path, str):
            keys = path.split(sep)
        elif isinstance(path, int):
            keys = path
        else:
            keys = path

        assert keys
        last = keys[-1]
        key = ""
        for key in keys[0:-1]:
            _data = _data[key]

        return (_data, last)

    @classmethod
    def get(cls, _data: Mapping, path: str | int | Iterable, sep: str=".", default: Any = DEFAULT) -> Any:
        try:
            _data, key = cls.walk(_data, path, sep)
            return _data.get(key, default)
        except Exception as exc:
            raise Exception(f"ConfigDict: Value not found: '{path}'") from exc

    @classmethod
    def delete(cls, _data: Mapping, path: str | int | Iterable, sep: str=".", exception: bool = True) -> Any:
        try:
            _data, key = cls.walk(_data, path, sep)
            del _data[key]
        except Exception as exc:
            if exception:
                raise Exception(f"ConfigDict: Value not found: '{path}'") from exc

    @classmethod
    def set(cls, dict: Mapping, key: Any, value: Any) -> Any:
        pass


class MyLoader(yaml.SafeLoader):

    def __init__(self, stream) -> None:
        super().__init__(stream)

        self.stack = []

    def on_value(self, node, obj) -> YamlObj:
        return YamlObj(
            node.start_mark.line + 1,
            node.start_mark.column + 1,
            node.start_mark.name,
            obj
        )

    def construct_scalar(self, node):
        obj = super().construct_scalar(node)

        if self.stack:
            last = self.stack[-1]
            last.incr()
            if isinstance(last, YamlSequence):
                return self.on_value(node, obj)

            if isinstance(last, YamlMapping) and (last.count & 1) == 0:
                return self.on_value(node, obj)

        return obj

    def construct_sequence(self, node, deep=False):
        self.stack.append(YamlSequence(0))
        obj = super().construct_sequence(node, deep)
        self.stack.pop()
        return obj

    def construct_mapping(self, node, deep=False):
        self.stack.append(YamlMapping(0))
        obj = super().construct_mapping(node, deep)
        self.stack.pop()
        return obj


class CompoundValue(list):

    def __init__(self, values: Iterator['ValueType']) -> None:
        super().__init__(list(values))

    def is_import(self) -> bool:
        for elem in self:
            if isinstance(elem, ImportPlaceholder):
                if len(self) != 1:
                    raise ValueReaderException("Invalid '{import: ...}', ${elem}")

                return True

        return False

class JDConfig:

    def __init__(self) -> None:
        pass

    def load_yaml_raw(self, fname: Path) -> Mapping:
        # pyyaml will consider the BOM, if available,
        # and decode the bytes. utf-8 is default.
        with open(fname, "rb") as fd:
            loader = MyLoader(fd)
            return loader.get_single_data()

    def load(self, fname: Path) -> Mapping:
        _data = self.load_yaml_raw(fname)

        imports: dict[Any, ImportPlaceholder] = {}
        for path, obj in objwalk(_data):
            value = obj.value
            if isinstance(value, str) and value.find("{") != -1:
                value = obj.value = CompoundValue(ValueReader().parse(value))
                if value.is_import():
                    imports[path] = value[0]

        for path, obj in imports.items():
            import_data = self.load(obj.file)
            if obj.replace:
                ConfigGetter.delete(_data, path)
                _data.update(import_data)
            else:
                _data[path] = import_data

        return _data


ValueType: type = Union[int, float, bool, str, 'Placeholder']

@dataclass
class Placeholder:
    name: str
    args: List[ValueType]

@dataclass
class ImportPlaceholder(Placeholder):

    @property
    def file(self) -> str:
        return self.args[0]

    @property
    def env(self) -> str | None:
        if len(self.args) > 1:
            return self.args[1]
        return None

    @property
    def replace(self) -> bool:
        if len(self.args) > 2:
            return bool(self.args[2])
        return False

class ValueReaderException(Exception):
    pass

class ValueReader:

    def parse(self, strval: str, sep: str = ",") -> Iterator[ValueType]:
        stack: List[Placeholder] = []
        _iter = self.tokenize(strval, sep)
        try:
            while text := next(_iter, None):
                if text == "{":
                    name = next(_iter)
                    colon = next(_iter)
                    assert colon == ":"
                    placeholder = Placeholder(name, [])
                    if name == "import":
                        placeholder.__class__ = ImportPlaceholder
                    stack.append(placeholder)
                elif text == "}" and stack:
                    placeholder = stack.pop()
                    if not stack:
                        yield placeholder
                    else:
                        stack[-1].args.append(placeholder)
                else:
                    if not stack:
                        yield text
                    else:
                        value = self.convert(text)
                        stack[-1].args.append(value)
        except StopIteration as exc:
            raise ValueReaderException(
                f"Failed to parse yaml value with placeholder: '${strval}'") from exc


    def tokenize(self, strval: str, sep: str = ",") -> Iterator[str]:
        start = 0
        i = 0
        while i < len(strval):
            c = strval[i]
            if c == "\\":
                i += 1
            elif c in ['"', "'"]:
                i = self.find_closing_quote(strval, i)
                yield strval[start + 1 : i - 1]
                start = i + 1
            elif c in [sep, "{", "}", ":"]:
                text = strval[start : i].strip()
                if text:
                    yield text
                start = i + 1

                if c is not sep:
                    yield c

            i += 1

        text = strval[start : ].strip()
        if text:
            yield text


    def find_closing_quote(self, strval: str, start: int) -> int:
        quote_char = strval[start]
        i = start + 1
        while i < len(strval):
            c = strval[i]
            if c == "\\":
                i += 1
            elif c == quote_char:
                return i

            i += 1

        return i - 1


    def convert(self, strval: str) -> int | float | str:
        possible = [convert_bool, int, float, str]
        for func in possible:
            try:
                return func(strval)
            except (ValueError, KeyError):
                continue

        return strval


def convert_bool(strval: str) -> bool:
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

if __name__ == '__main__':
    data = JDConfig().load("./comlify/config.yaml")
    assert ConfigGetter.get(data, "a").value == "a"

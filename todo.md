# Todos / Requirements

- I like structured configs with dataclass and pydantic
- support making a subtree read-only
- We construct one config "dict", not multiple layers as we had earlier. But we need
  some debugging, tracing/logging. May be a list of add/change/deletes with filename
  and line number? Also when replacing syntax with real values. Why not replace the
  values eagerly? => Because if the referenced value changes, then its outdated.
- Maybe we should additional have std yaml '!include config.yaml'
- Error handling must be much improved
- I'm no longer 100% convinced that keeping filename, line, and col is adding lots of value
  Can we make this flexible, such as that we have 2 implementations and both are working fine?
- It happens regularly to me, that I forget to put quotes around {..}.
  Maybe ${..} or $(..). How would a yaml parser handle ${..} ??
- Allow the env overlays to be in a different directory. Does that make any sense?
- Env placeholders could be resolved early. We need a generic approach, that allows
  the placeholder implementation to decide.
- Recursion: identify when {ref:} goes in circles, referencing each other, and
  report an error.
- Not 100% the effort with preprocessing creates enough value, vs. lazy (and repeated)
  evaluation of {..} constructs.
- Support env sepcific yaml config files in working directory (not required to be in config dir)
- Allow {import: https://} or {import: git://} or redis:// or custom => registry wit supported protocols
- Separate the loader and access to the config data. Add DeepAccessMixin to config, not loader.
- When dumping config, allow to add file, line, col as comment for debugging.
- For debugging, log placeholder replacements

Done:

- OmegaConf can use directories, e.g. to support mssql, postgres, oracle, or
  kafka and red panda, or AWS EKS, RH OpenShift, Tanzu. Several configs are the same,
  but each ones has specific configs as well.
- I'm not 100% a fan of OmegaConf's "default", _self_, and "magical" sequences. I want
  something more obvious. Thus "import" statements
- I prefer {ref:..} over yaml &id and \*id.
- I like {ref: xxx, <default>} to support default values
- I like {env: xxx, <default>} to support default values
- I like ??? for mandatory values.
- I like lazy value resolution, except for {import:..} which should eagerly load
  the files.
- I like all the different access methods xyz[a][b], xyz.a.b, xaz.a[3].d.e[1], xyz/a/b
  - alongside get(...)
- I like to register additional operands, such as ref, env, import, ...
- also support setting configs (not just reading)
- Our "loader" will first read the yaml as-is, then recursively walk the elements
  and pre-process the special syntax elements.
  Configurable, some operators are processed eagerly (e.g. import, env), others,
  e.g. put a CompoundValue object. CompoundValue is essentially a list of scalars and
  Operands such as EnvOperator, ImportOperator, RefOperator, .... So that we need
  to analyse just ones. We may also cache values for speed. (cache the whole value,
  not just the operands value)
- {import:} may cause recursive loads => Auto-detect
  A file might by purpose be loaded multiple times, but recursions are not allowed.
- to_yaml(); to_dict(<type> = dict); auto-resolve
- separate resolve() function, which also works in containers. Not just a value.
- {import:} should support in-place and "in parent/root". e.g.
  - xyz: {import: xyz} # load in xyz
  - abc: {import: abc, True} # load into abc parent == root.
- yaml tags, e.g. !import, !env etc.. These tags are eagerly executed in yaml (add_constructor).
  With our syntax {xyz:..}, they become strings and we must analyze them ourselves.
- I like OmegaConf {xyz:..} constructs. But I don't like {oc.env:...}
- dynamic {import: ./db/{ref:db}-config.yaml} now working with env. Restriction: manually
  changing "db" will not important the other file. Ofcourse you can always load and set()
  the other file manually.
- {import: ..., replace=True}: replace arg no longer supported
- made get("path") mor strict, e.g. "a", "a[1]b", but not "a.1.b". List are always[].
- Do we need items(), iter(), keys(), [key] for the config items? => No
- added `".."`, `".*.\"` and `"[*]"` support, e.g. get("c..c32").
- we are using get(), but not yet obj[] and obj.x.y.n => Not adding enough value. get()
  is more flexible, also supporting e.g. `"c..c32"` and `"c.*.c32"`
- log warning for {import:} with absolute file path
- Recursion: identify when {ref:} goes in circles, referencing each other, and
  report an error.

# Nice to know

- Dynamically add a base class (or mixin)

  ```
    p.__class__ = type('GentlePerson',(Person,Gentleman),{})
    class Gentleman(object):
      def introduce_self(self):
        return "Hello, my name is %s" % self.name

    class Person(object):
      def __init__(self, name):
        self.name = name

    p = Person("John")
    p.__class__ = type('GentlePerson',(Person,Gentleman),{})
    print(p.introduce_self())
    # "Hello, my name is John"
  ```

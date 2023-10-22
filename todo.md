# Todos / Requirements

- I like structured configs with dataclass and pydantic
- We construct one config "dict", not multiple layers as we had earlier. But we need
  some debugging, tracing/logging. May be a list of add/change/deletes with filename
  and line number? Also when replacing syntax with real values. Why not replace the
  values eagerly? => Because if the referenced value changes, then its outdated.
- Error handling can be improved. Done, except filenames
- I'm no longer 100% convinced that keeping filename, line, and col is adding lots of value
  Can we make this flexible, such as that we have 2 implementations and both are working fine?
- It happens regularly to me, that I forget to put quotes around {..}.
  Maybe ${..} or $(..). How would a yaml parser handle ${..} ??
- Allow the env overlays to be in a different directory. Does that make any sense?
- Env placeholders could be resolved early. We need a generic approach, that allows
  the placeholder implementation to decide.
- Support env sepcific yaml config files in working directory (not required to be in config dir)
- Allow {import: https://} or {import: git://} or redis:// or custom => registry wit supported protocols
  Some may provide files, others leverage SDKs which provide a Mapping. We need to support both.
- When dumping config, allow to add file, line, col as comment for debugging.
- For debugging, log placeholder replacements
- Make sure that {env:} results are not resolved any further. Else risky configs might be
  injected.
- Add {delete:} to allow env files to remove a node
- Config from remote: How should the config.ini look like, and the plugin config, to retrieve such configs

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
- env file updates do not support deletes, or add elems to lists. We had this for some
  time, but it proofed dangerous in production. Same for search patterns. Maybe nice
  for developers, we qa/prod envs, it caused suptle issues, not obvious/easy to detect
  by operations. Even with config.dump() cli features, which ops may not be aware of.
  It may work with devops teams, where dev and ops are working in one team, but
  unfortunately that is rarely the case. And the "workarounds" make it very obvious:
  copy the file, append the env name, and simply change them. If we don't support
  deletes, how to replace dicts and lists, vs. values only? (see test cases)
- on missing, it should not be required to add the new object to the parent.
- Maybe we should additional have std yaml '!include config.yaml' => No. {import:} is
  more flexible and consistent
- Not 100% sure the effort with preprocessing creates enough value, vs. lazy (and repeated)
  evaluation of {..} constructs. => all lazy right now
- Separate the loader and access to the config data. Add DeepAccessMixin to config, not loader.
- We need a more *efficient* walk implementation. One that supports `a.b[2]` but also `c..c2[*]`
- {global:} is only a stub so far, but not yet implemented
- Implemented r".." for raw text, which will not be interpreted
- CONFIG_INI_FILE env to find config.ini file => now possible to provide env var name
- Allow to use any *.ini file, since we just use the [config] section => done
- right now we are re-importing config file all the time => cache
- may be add some stats feature: number of config values; list imported files; number of {ref:},
  max depth; list of envs referenced;
- add "__file__" to the config for easy access? Alternative: a simple class consisting
  of file name and data? Essentially dict extended with file_name attribute? => create ConfigFile
- test {import:} with env specific overlay

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

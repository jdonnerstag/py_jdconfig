# Todos / Requirements

- Pydantic challenges:
  - to support {ref:} and {global:} we need to pass meta data to each BaseModel subclass,
    e.g. parent: ConfigBaseModel | None, data: ContainerType, file: ConfigFile, root: ConfigFile
    Even though pydantic has private keys, I do not know how to pass the meta data,
    when a config is loaded and pydantic creates models. I found create_model(), but it doesn't
    provide me the parent (caller). Does BaseModel has a method (overwrite) to create a submodel?
    Validate "before" is a classmethods. Only "after" is an instance method.
    validate "wrap" example: https://stackoverflow.com/questions/77007885/pydantic-v2-model-validatormode-wrap-how-to-use-modelwrapvalidatorhandl
  - I'd like to remember the original value, e.g. "{ref:a}" or "{import:./{ref:db}/abc.yaml}",
    to dynamically resolve the value (always running the validator). Because I want to be able
    to change "db" and node importing data, will AUTOMATICALLY be updated.
  - How to still load into a dict?
    Deep structures as well, AND with resolving.
    And support types, such as dict[str, str|int]
  - Support for Union types, with predicators to determine which type to apply.
  - class name and yaml var name can be different
  - add something that resolves all by replacing the "{..}" with actual values.
    Why is that useful?
  - min_len, max_len, func, etc. to Field
- improve error reporting and debugging as we did before
- test case w/o any class, just dict => we need at leat a DummyModel with just
  one dict attr. But we should test, that the dict values do get resolved.
- test cases for subclasses with both having attributes
- I don't think we have cli test cases?
- A test case that combines Field and a placeholder
- Support for ".." and "." in {ref:}
- is there already support for: easy: container: dict[str, MyClass]
  container:
    abc: dict/node with data of type X
    def: same base model a "abc"

- It happens regularly to me, that I forget to put quotes around {..}.
  Maybe ${..} or $(..). How would a yaml parser handle ${..} ??
- Env placeholders could be resolved early. We need a generic approach, that allows
  the placeholder implementation to decide.
- When dumping config, allow to add file, line, col as comment for debugging.
- Make sure that {env:} results are not resolved any further. Else risky configs might be
  injected.
- Add {delete:} to allow env files to remove a node
- Config from remote: How should the config.ini look like, and the plugin config, to retrieve such configs
  .e.g. providers = ["myproject.MyProvider"]
- should {a.b.c} or {:a.b.c } == {ref:a.b.c} with {ref:} as default?
  Is "{:" allow at all right now? May be that is an easy fix
- Evaluate further get("..") vs cfg.a.b.c.  I still prefer get("..") which avoids confusions IMHO, allow
  "a.**.c", and "../ab" etc, which is not possible with x.a.b.c => Don't think that is correct!!
- struct configs => configs are mostly readonly; dataclasses; pydantic; support to read
  configs (subsections) into a dataclass (logging, ETL, other modules and their configs). Every
  app consists of other modules. Don't want to redo structured config for every module all the
  time => Modules responsible for details. E.g. cfg.get(path, into=type or instance) which
  retrieves the config for path, and loads the data into type.

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
- We construct one config "dict", not multiple layers as we had earlier. But we need
  some debugging, tracing/logging. May be a list of add/change/deletes with filename
  and line number? Also when replacing syntax with real values. Why not replace the
  values eagerly? => Because if the referenced value changes, then its outdated.
- Error handling can be improved.
- For debugging, log placeholder replacements
- Added "*.*." search support.
- More and import debug log message.
- I'm no longer 100% convinced that keeping filename, line, and col is adding lots of value
  Can we make this flexible, such as that we have 2 implementations and both are working fine?
  Abondaned the idea, now that we have much improve logging (debug)
- Allow the env overlays to be in a different directory.
- Support env sepcific yaml config files in working directory (not required to be in config dir)
- Replaced "a..b" search pattern with "a.**.b"
- Added support for relative references, e.g. {ref:../../abc} or {ref:./abc}, in contrast to
  reference relative to the file root.
  Was thinking about "..[2]" == "../.." but I don't like it. Too unusual.
  "...a.b" == "../a/b" => No. How should "../../a" then look like?
  Mixing multiple sep as in "../a.b" => No, only creating confusion
  {ref:a/b/c, sep="/"} to make it explicit? => Not yet implemented. Still needed?
  Can we auto-detect whether it is "a/b/c" or "a.b.c"? => we now do. precendence order: "/."
- Make ConfigPath a class that holds the path, not just the conversion. Replace
  tuple(str|int, ...) with this class, which is more explicit
- Separate CfgPath into Base and Extended
- A little cli to dump (resolved) configs, list stats, find keys or values
- resolve_eagerly still adding value? Use jdconfig.resolve_all() instead
- Allow {import: https://} or {import: git://} or redis:// or custom => registry wit supported protocols
  Some may provide files, others leverage SDKs which provide a Mapping. We need to support both.
  => see provider registry
- the env overlay should allow "a.b.c: 10" instead of "a: {b: {c: 10}}". Or may be not? => Not
- CLI: add more reasonable default log formatting

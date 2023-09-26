
# Todos / Requirements

- I want to easily support multiple envs (e.g. dev, test, prod, ..)
  - It should be possible to commit them all into github, without them interfering
  - Many configs are the same across all envs, but infra is different. Make it easy
    to indentify and manage all envs specific changes (no copy and modify)
  - How to: the issue is with {import: ./db/{ref:db}-config.yaml}, where the path is dynamic. Imagine the env overlay want to change from oracle to postgres. So in your overlay you overwrite db: "oracle" to db: "postgres". How needs the load process to be.
  Option 1a:
    - load the base yaml file (without imports)
    - load the env yaml file (with imports)
    - resolve the {import:} path first against the env vars, and only then the base.
      - CLI args almost overwrite any file. Meaning, if "db" provided via cli, we can ignore any env file and load directly.
    - Execute the import
    - merge the env vars
  Option 1b:
    - load the base yaml file (without imports)
    - load and merge the env yaml file (with imports)
    - Execute {import:} on merged var very normaly
    - merge the env vars again, because the import-merge might have replaced some.
      Note on merge: dict.update() will not work. Deep-update should only replace the leafes in the env file.
  Option 2:
    - load the base yaml file (with imports)
      - and remember the node and import file name
    - load the env yaml file (with imports)
    - merge the env vars
    - re-evaluate import path, with env overwrites, and possibly reload the file.
    - if changed, the merge again the env vars
  Option 3:
    - extend config.ini to hold the "db" variable. Requires env specific config.ini support. Which is tricky, because config.ini defines the env name. It also diludes config.ini, which should be jdconfig configs only (not user configs).
  - Changing "db" in your app, it will not reload the dynamic imports.
    Which requires that we remember the import node, and the import placeholder details, incl the ref var. Would this also work when overloading with env? It would still first load the main imports, and then import the env one.
- I like structured configs with dataclass and pydantic
- support making a subtree read-only
- We construct one config "dict", not multiple layers as we had earlier. But we need
  some debugging, tracing/logging. May be a list of add/change/deletes with filename
  and line number? Also when replacing syntax with real values. Why not replace the
  values eagerly? Because if the referenced value changes, then its outdated.
- Maybe we should additional have std yaml '!include config.yaml'
- Error handling must be much improved
- I'm no longer 100% convinced that keeping filename, line, and col is adding lots of value
- It happens regularly to me, that I forget to put quotes around {..}.
  Maybe ${..} or $(..). How would a yaml parser handle ${..} ??
- Allow the env overlays to be in a different directory. Does that make any sense?
- Env placeholders can resolved early. We need a generic approach, that allows
  the placeholder implementation to decide.
- Recursion: identify when {ref:} goes in circles, referencing each other, and
  report an error.
- Not 100% the effort with preprocessing creates enough value, vs. lazy (and repeated)
  evaluation of {..} constructs.
- I don't think we need / should support {import: ..., replace=True}
- we are using get(), but not yet obj[] and obj.x.y.n

Done:
- OmegaConf can use directories, e.g. to support mssql, postgres, oracle, or
  kafka and red panda, or AWS EKS, RH OpenShift, Tanzu. Several configs are the same,
  but each ones has specific configs as well.
- I'm not 100% a fan of OmegaConf's "default", _self_, and "magical" sequences. I want
  something more obvious. Thus "import" statements
- I prefer {ref:..} over yaml &id and *id.
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
  - xyz: {import: xyz}   # load in xyz
  - abc: {import: abc, True}  # load into abc parent == root.
- yaml tags, e.g. !import, !env etc.. These tags are eagerly executed in yaml (add_constructor).
  With our syntax {xyz:..}, they become strings and we must analyze them ourselves.
- I like OmegaConf {xyz:..} constructs. But I don't like {oc.env:...}

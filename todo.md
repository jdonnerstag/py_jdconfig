
# Todos / Requirements

- I want to easily support multiple envs (e.g. dev, test, prod, ..)
  - It should be possible to commit them all into github, without them interfering
  - Many configs are the same across all envs, but infra is different. Make it easy
    to indentify and manage all envs specific changes (no copy and modify)
- OmegaConf can use directories, e.g. to support mssql, postgres, oracle, or
  kafka and red panda, or AWS EKS, RH OpenShift, Tanzu. Several configs are the same,
  but each ones has specific configs as well.
- I'm not 100% a fan of OmegaConf's "default", _self_, and "magical" sequences. I want
  something more obvious. Thus "import" statements
- I like OmegaConf {xyz:..} constructs. But I don't like {oc.env:...}
- I prefer {ref:..} over yaml &id and *id.
- I like {ref: xxx, <default>} to support default values
- I like {env: xxx, <default>} to support default values
- I like ??? for mandatory values.
- I like lazy value resolution, except for {import:..} which should eagerly load
  the files.
- I like all the different access methods xyz[a][b], xyz.a.b, xaz.a[3].d.e[1], xyz/a/b
  - alongside get(...)
- I like structured configs with dataclass and pydantic
- {import:} may cause recursive loads => Auto-detect
- I like to register additional operands, such as ref, env, import, ...
- {import:} should support in-place and "in parent/root". e.g.
  - xyz: {import: xyz}   # load in xyz
  - abc: {import: abc, True}  # load into abc parent == root.
- also support setting configs (not just reading)
- support making a subtree read-only
- to_yaml(); to_dict(<type> = dict); auto-resolve
- separate resolve() function
- yaml tags, e.g. !import, !env etc.. These tags are eagerly executed (add_constructor).
  With our syntax {xyz:..}, they become strings and we must analyze them ourselves.
- Our "loader" will first read the yaml as-is, then recursively walk the elements
  and pre-process the special syntax elements.
  Configurable, some operators are processed eagerly (e.g. import, env), others,
  e.g. put a CompoundValue object. CompoundValue is essentially a list of scalars and
  Operands such as EnvOperator, ImportOperator, RefOperator, .... So that we need
  to analyse just ones. We may also cache values for speed. (cache the whole value,
  not just the operands value)
- We construct one config "dict", not multiple layers as we had earlier. But we need
  some debugging, tracing/logging. May be a list of add/change/deletes with filename
  and line number? Also when replacing syntax with real values. Why not replace the
  values eagerly? Because if the referenced value changes, then its outdated.

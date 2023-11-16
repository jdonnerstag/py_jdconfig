
# The idea of this branch/version

We have the "deep getter + context" approach, and a pydantic inspired one.
As discussed further below, I prefer clean separation and flexibility. E.g.
let attrs and pydantic do, what they can do best. Which is part of a settings
or config mgmt system. I want *.ini support, and optionally a template system
to resolve references or import other files. I have no preference if someone
wants to it in the template, or in attrs/pydantic. I want envrionment specific
overlays, in whatever form. But flexible to allow for different options.

Both current implementations have pros and cons. Am not 100% happy with either.
This version/branch applies lessons learnt from both. I call it the "wrapper"
approach for now.


# The idea of this branch/version (old)

We have different implementations so far:
- deep getter based and with template engine
- My own, pydantic inspired, BaseModel and runtime type checker

We want config.ini support, and we want environment specific overlays (dev, test,
prod, etc.) in whatever form. The pydantic-like approach puts a lot of logic
in the BaseModel(s). Which works, but may be is not especially clean or modular.
The BaseModel is very flexible, but because it uses inheritance, all its functions
(their names) might interfere with user attributes.

To support config.ini and env specific overlays, we anyway need something
similar to an App object (Config, Settings) which manages these things. It's bit like a
pipeline: initilize config.ini -> load any json/yaml file -> apply env overlay(s)
-> cli args -> optional template engine -> attr or pydantic or .. I want this pipeline
to be configurable (tuple, list)

Except for the last step, it is fairly standard config mgmt, with conversion
and validation happening in the last step.

Lazy resolution: We did not find a good use case, why this is an important
  requirement. Config data are rather static.

When changing a value, e.g. "db: oracle" to "db: postgres", we want
"database: {import: ./db/{db}-config.yaml}" to load the database specific
config file. It is a valid use case, except that this change must be possible
at runtime. How often does it happen with configs, that you first load database A,
then you change the setting to select database B? The database is part of the
environment, and you set it ones.

I want generic support for vaults (as in environ-config).

Users may freely choose between {env:} and field(env=). Whichever they prefer.
Same for {import:} and field(import_file=)

# Pydantic

As mentioned, I like pydantic, but only recently learnt about pydantic-setting.
The following are use cases, which I'd like to validate. Regarding the solution
I want to be open. Only because we've solved it one way in the past, doesn't
mean it is the only one, or most appropriate one.


## Use case 1: Env overlay in json (vs. env vars)

Requirement: Environment specific changes, e.g. dev, test, QA, prod, etc. are important.
It should be possible to have many (e.g. by name), and they should not
interfere with production. And it should be possible to commit them in
git, if wanted.

pydantic-settings provides ootb support for env vars. And dotenv files, for
multiple env vars. pydantic settings explodes e.g. "x.y.z = 1" in {x: {y: {z: 1}}} and
will merge the dicts from multiple vars. I need to see how this works for our apps.

The homepage also has code to use a json file in cwd. Which is more like what we have
done so far.

Which implies that after reading the json/yaml/whatever data, we need to merge it first
with the env overlay, and only then create the class. Which means, that some sort
of Config class still makes sense. To load the files from a config dir, read config.ini,
and so on. May be, this packages can work with both, pydantic and attrs?

## Use case 2: config.ini

Requirement: Many packages, e.g. pytest, support *.ini files. We are using *.ini files in
many of our apps as well, often with a [config] section for config related settings. Note
that the ini files is a combined one, not only config. And it is not replacing the json/yaml
config files, but is only used for few core settings, usually needed to load the json/yaml
files. E.g. the ./config dir, or the main config file, e.g. config.yaml, the env name, e.g.
mydev, qa, ..; or configs which otherwise would need to be provided via the cli.

pydantic allows to load *.ini data into pydantic models, and use the info to
load the config files. It is all there, except you need to glue it all together
yourselve.

## Use case 3: Settings in multiple files

Requirement: We often split configs into multiple files. How to load / combine them?

Ideas:
1. Something like an 'database: OracleSettings = Import(<filename>)" Field descriptor.
2. a config.ini entry such as "database = <filename>"
3. may be auto-load all files in the direc, dynamically creating/assign them to vars
   which have the filename.
4. Use {import:<filename>} in the json or yaml file.
5. manually load the file and assign it to the var.

To me, this is important enough, to not rely on a manual approach (5).
The all directory approach (3) is also not good. First, I like it explicit and 2nd the var name
would be the filename? That will definitely lead to issues.
The template approach (4) is only an option if there is the need for more {..} placeholders,
not just {import:}
I prefer (1) over (2) because, it'll more obvious when reading the code.

Pydantic and attrs allow to define (with some differences) validators, which are executed
after the data have been loaded. Or altenatively __post_init__. Which might be a good time
to import the other file? The field type should another basemodel, dict or list, but no
str, int, float, etc. Which would'nt make sense I guess. May be str does.

## Use case 4: dynamic import files

Requirement: Imagine something like:
  db: oracle
  database: {import: ./db/{ref:db}-config.yaml}

It has 2 aspects: There is a dependency on another variable. And the setting for each database
will be different. Oracle has different settings, then postgres or mysql or ...
And when changing thr "db" value, you want to change the "database" as well.

Many config systems leverage a template engine, to resolve the placeholders when reading
the var. Is there maybe a more pydantic-like approach? One that builds upon the
"Settings in multiple files" use case?

__post_init__ and validators are executed AFTER the data have been loaded. Hence they have
access to other variables and can use them. That should work. At least as long the variable
as in the same class.

## Use case 5: References

Requirement: In json/yamls file we enjoy the ability to reference other value (absolut
but also relative to root). As a whole, but also embedded, as in {import(./db/{ref:db}-config.yaml)}.
E.g. at the beginning we define all the directories, and later we reference them
when defining the files. Having it in the config file makes it very obvious, and a model
dumper prints the final value; easy to validate/debug.

Since we need a "loader" anyway, maybe we can define a execution pipeline. I belief
pydantic and attrs have something similar for a different use case. That pipeline could
easily be explanded with any template engine.

## Use case 6: Pluggable secret provider

I really like the pluggable secret provider (see below)


# TODO I should take a look at python attrs package as well.

attrs seems to be a bit cleaner to me, more structured and thus more flexible, compared
to pydantic. And this (lack of) flexibility lend me to start developing my own
config system.

https://threeofwands.com/why-i-use-attrs-instead-of-pydantic/.
https://stefan.sofa-rockers.org/2020/05/29/attrs-dataclasses-pydantic/

What I like better in pydantic is that validators are much more readable, e.g.
email, credit card numbers, RedisDNS, String(minlen, maxlen,..), IntRange(..), ...

attrs, and pydantic as well(?), generate static method such __eq__, __repr__ and so on.
I've no idea how they do this, but may be we can expand on it to create boilerplate
config specific setting etc..

environ-config is an attr base setting systems, which heavily relies on Env vars. In
my experience, this is only suitable for very small tools, if any. It has 2 features
though which I like:
- Nested configuration from flat environment variable names.
  - I'd prefer something like "x: int = field(env="MY_ENV", converter=int)" which makes
    it obvious and easy to use.
- Pluggable secrets extraction. Ships with:
  - HashiCorp Vault support via envconsul.
  - AWS Secrets Manager (needs boto3)
  - INI files, because secrets in env variables are icky.

The use cases mentioned further up, remain our key reqs though.

# My thoughts on this approach: pydantic like

The previous approach (branch) reads (and resolves) dict-like configs with
a deep getter, and if a user wants an object (class, model), it is easy to
use pydantic to convert it. This raised the question, why not a use a pydantic
like right from the beginning. A BaseModel that loads the data and stores them
in user defined, and typed, variables. I really like pydantic but couldn't figure
out to use it.
So I build my own BaseModel and Runtime Type Checker, with type conversions
included. That is this branch. I'm quite ok with the implementation, and it
is working well. Pydantic is tuned for speed and efficiency, which my approach
obviously is not. But the use case is different (configuration) and speed not
my primary concern. Also configs are usually not huge, like mega bytes or
thousands of config params. Hence (memory) efficiency is not a must. But the
current implementation adds to every BaseModel some extra mgmt related
data. This is because pydantic does it magic upon creating the class instance,
whereas my approach (and lazy resolution) requires to keep some info. You
change a value, and lazy resolution will provide you the updated and validated
values which have references to the changed value.

I like the Runtime TypeChecker. It works well, and it was a good learning
excercise.

The current implementation does its job nicely (except better errors / tracing /
debugging) and few minor things.

This is a pydantic first approach. It allows to use dicts and lists to load
configs into, but its primarily classes. Whereas the deep getter approach is
primarily dict/lists loaded from yaml/json files, with the additional option
to load nodes into classes. ith the getter approach you need to change the deep
dict to make changes, and reload with pydantic. In the pydantic-like approach
you change the object. Changes to the dict have no effect.

The pydantic/class approach puts more focus on validation, because basically
every config item, must have a attr in the base model (else it'll be ignored).
You end up definining a number of classes, one per dict-node in the config.


# Python Configuration Management

Still not 100% happy with the various (python) config managment packages,
I started with my own.

I recently read about Hydra and OmegaConf, and even though I mostly liked it,
in my humble opinion, it can be improved.

Most importantly, support for multiple environments, such as dev, test,
pre-prod and prod. We've made good experience with environment specific overlay
files, containing just the changes necessary for a specific environment. Without
changing the ones for production.

We'd like to support remote config stores, such as etcd, AWS Parameter Store,
NoSQL databases, or plain web servers, ... Or at least provide the flexibility
to easily plugin adapters.

A more complete list of requirements can be found below

# Introduction

# Structered Configs

- Configs are mostly read-only. Often, they are manually created and updated,
  hence human mistakes are very common, thus validation is very important.
- Most configs are yaml, json, ini or the like, which do not provide any validation.
  The structure and the values are only validated upon the app reading the configs.
- A config system should support all kind of applications. Everything but
  scripts or small apps, consist of a varity of modules. These modules are often
  re-useable and applied in different contextes in different apps. Most modules
  require some sort of config, e.g. databases, directories, cloud configs, pipelines,
  and so on. The config for all modules that make up an app, should come from one
  config system. Hence, the logic to validate configs should be with the modules
  (and not the config system). The config system should provides hooks or support or
  best practices, to make it as easy as possible.
- E.g. modules might register their config getters or validators, which might as
  well convert the dict/list like structures into dataclasses or the like.
- It would be nice, if the little config CLI would also know about these getters,
  to be able to validate configs without running the app itself.

# Requirements

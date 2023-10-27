
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

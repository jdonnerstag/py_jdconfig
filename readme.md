
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


# Requirements

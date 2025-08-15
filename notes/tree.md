tree . -L3
.
├── CONTRIBUTING.md
├── docs
│   ├── api
│   │   ├── auth.md
│   │   ├── index.md
│   │   └── routes.md
│   ├── architecture
│   │   ├── data-flow-diagram.md
│   │   ├── index.md
│   │   ├── matching-layers.md
│   │   ├── storage.md
│   │   ├── system-diagram.md
│   │   └── workflow-generation.md
│   ├── development
│   │   ├── domain-management.md
│   │   ├── getting-started.md
│   │   └── ome-mvp-plan.md
│   ├── domains
│   │   ├── cooking.md
│   │   ├── index.md
│   │   └── manufacturing.md
│   ├── index.md
│   ├── models
│   │   ├── bom.md
│   │   ├── index.md
│   │   ├── okh-docs.md
│   │   ├── okw-docs.md
│   │   ├── process.md
│   │   ├── supply-tree.md
│   │   └── validation.md
│   └── overview.md
├── LICENSE
├── mkdocs.yml
├── notes
├── pyproject.toml
├── README.md
├── requirements.txt
├── run.py
├── src
│   ├── __init__.py
│   ├── config
│   │   ├── __init__.py
│   │   ├── domains.py
│   │   ├── settings.py
│   │   └── storage_config.py
│   └── core
│       ├── __init__.py
│       ├── api
│       ├── domains
│       ├── main.py
│       ├── models
│       ├── registry
│       ├── services
│       ├── storage
│       └── utils
└── tests
    ├── harness.py
    ├── results
    ├── run_tests.py
    ├── test_runs.log
    └── test_storage_handlers.py
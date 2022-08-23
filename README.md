# publications

SuttaCentral books: make HTML, EPUB, PDF

Central repo for SuttaCentra;s' publications WIP.

<https://github.com/orgs/suttacentral/projects/2/views/1>

## Requirements
* [Python 3.10](https://www.python.org/)
* Docker and docker-compose

## How to use
### Development stack

Clone repo

In general for this to function first you need to set up this repo: [suttacentral/suttacentral](https://github.com/suttacentral/suttacentral).

Install pre-commit git hooks:

1. First install dependencies (libraries responsible for formatting). You fill find them in Makefile#lint
e.g.
    ```bash
    pip install black isort mypy bandit autoflake
    ```
2. Then install the actual pre-commit hook
    ```bash
    # Go to project root
    cd publications

    # Make sure the file is executable
    chmod +x pre-commit

    # Install it
    cp pre-commit .git/hooks
    ```

It will mount the project root to the container:
```bash
# Build dev docker image
make build IMAGE_TARGET=development

# Run dev console to fiddle
make run-bash

# Tests
# if needed:
make build IMAGE_TARGET=development
# and
make test or make test-ci

# Lint code
# if needed:
make build IMAGE_TARGET=development
# and
make lint
```

### Production stack
```bash
# Go to project root
cd publications

# Run the script with given args
make run -- <script_args>
```


# Maintenance
## Requirements file
Project uses [pip-tools](https://github.com/jazzband/pip-tools) to handle dependencies in `requirements/*.txt` files.
To manage requirements you need to have `pip-tools` installed in your env (or run docker for devs `make build-dev; make run-dev bash`).
Packages name used in this project are stored in `requirements/*.in`.
[Guide](https://code.kiwi.com/our-comprehensive-guide-to-python-dependencies-8a5a4366a563) on how to resolve conflicts and/or update dependencies.

### How to add new package
1. Add package name to suitable `requirements/*.in` file
2. Run command to propagate changes and pin the package number
```bash
# Compile requirements *.txt files based on *.in file content
make compile-deps
```

### How to update all requirements to new versions
```bash
# To update all packages, periodically re-run
make recompile-deps
```

### How to sync requirements with your virtual environment
```bash
make sync-deps
```

### How to build and publish new docker image

#### Production
```bash
# Build docker image to github
make build IMAGE_TARGET=production

# Push docker image to github
make push-docker-image IMAGE_TARGET=production
```

#### Development
```bash
# Build docker image to github
make build IMAGE_TARGET=development

# Push docker image to github
make push-docker-image IMAGE_TARGET=development
```

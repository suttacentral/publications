# publications

SuttaCentral books: make HTML, EPUB, PDF

Central repo for SuttaCentra;s' publications WIP.

<https://github.com/orgs/suttacentral/projects/2/views/1>

## Features
* [Python 3.10](https://www.python.org/)
* Docker and docker-compose

## How to use
### Development stack

Clone repo

Install pre-commit got hooks:
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
# Build dev image
make build-dev

# Run dev console to fiddle
make run-dev bash

# Tests
make test

# Lint code
make run-dev 'make lint'
```

### Production stack
```bash
# Go to project root
cd publications

# Build image
make build

# Run the script with given args
make run -- <script_args>
```

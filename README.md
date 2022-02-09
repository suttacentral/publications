# sutta_publisher

SuttaCentral publishing engine for HTML, EPUB, PDF.

https://github.com/orgs/suttacentral/projects/2/views/1

## Features
* [Python 3.10](https://www.python.org/)
* Docker and docker-compose

## How to use
### Development stack
It will mount the project root to the container.
```bash
# Go to project root
cd publications

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

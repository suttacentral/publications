PROJ_ROOT=$(dir $(abspath $(lastword $(MAKEFILE_LIST))))
PYTHON_EXEC?=python
COMPOSE_EXEC?=docker-compose

APP_PATH = src/sutta_publisher

LINT_PATHS = \
$(APP_PATH) \
tests


##############################################################################
### Run app
###########
run:
	$(COMPOSE_EXEC) -f ./deployment/docker/docker-compose.yml run publisher sutta_publisher $(filter-out $@,$(MAKECMDGOALS))


run-dev:
	$(COMPOSE_EXEC) -f ./deployment/docker/docker-compose.yml -f ./deployment/docker/docker-compose.dev.yml run publisher $(filter-out $@,$(MAKECMDGOALS))


build:
	$(COMPOSE_EXEC) -f ./deployment/docker/docker-compose.yml build publisher


clean:
	$(COMPOSE_EXEC) -f ./deployment/docker/docker-compose.yml rm -fsv
	$(COMPOSE_EXEC) -f ./deployment/docker/docker-compose.yml -f ./deployment/docker/docker-compose.dev.yml rm -fsv
##############################################################################


##############################################################################
### Testing
###########
build-dev:
	$(COMPOSE_EXEC) -f deployment/docker/docker-compose.yml -f ./deployment/docker/docker-compose.dev.yml build publisher


test: build-dev
	$(COMPOSE_EXEC) -f deployment/docker/docker-compose.yml -f ./deployment/docker/docker-compose.dev.yml run publisher pytest


test-ci:
	$(PYTHON_EXEC) -m autoflake --check --recursive --ignore-init-module-imports --remove-duplicate-keys --remove-unused-variables --remove-all-unused-imports $(LINT_PATHS) > /dev/null
	$(PYTHON_EXEC) -m isort --check-only $(LINT_PATHS)
	$(PYTHON_EXEC) -m black --check $(LINT_PATHS)
	$(PYTHON_EXEC) -m mypy $(APP_PATH) --ignore-missing-imports
	$(PYTHON_EXEC) -m bandit -r -q $(APP_PATH)
	$(PYTHON_EXEC) -m coverage run -m pytest
##############################################################################


##############################################################################
### Dependency & linting
########################
lint:
	$(PYTHON_EXEC) -W ignore -m autoflake --in-place --recursive --ignore-init-module-imports --remove-duplicate-keys --remove-unused-variables --remove-all-unused-imports $(LINT_PATHS)
	$(PYTHON_EXEC) -m black $(LINT_PATHS)
	$(PYTHON_EXEC) -m isort $(LINT_PATHS)
	$(PYTHON_EXEC) -m mypy $(APP_PATH) --ignore-missing-imports
	$(PYTHON_EXEC) -m bandit -r $(APP_PATH)


compile-deps:
	$(PYTHON_EXEC) -m piptools compile --no-annotate --no-header --generate-hashes "${PROJ_ROOT}/deployment/requirements/dev.in"
	$(PYTHON_EXEC) -m piptools compile --no-annotate --no-header --generate-hashes "${PROJ_ROOT}/deployment/requirements/prod.in"


recompile-deps:
	$(PYTHON_EXEC) -m piptools compile --no-annotate --no-header --generate-hashes --upgrade "${PROJ_ROOT}/deployment/requirements/dev.in"
	$(PYTHON_EXEC) -m piptools compile --no-annotate --no-header --generate-hashes --upgrade "${PROJ_ROOT}/deployment/requirements/prod.in"


sync-deps:
	$(PYTHON_EXEC) -m piptools help >/dev/null 2>&1 || $(PYTHON_EXEC) -m pip install pip-tools
	$(PYTHON_EXEC) -m piptools sync "${PROJ_ROOT}/deployment/requirements/dev.txt"
	$(PYTHON_EXEC) -m pip install -e .


# Silent unused rules
%:
	@:

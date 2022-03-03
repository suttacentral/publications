PROJ_ROOT=$(dir $(abspath $(lastword $(MAKEFILE_LIST))))
PYTHON_EXEC?=python
COMPOSE_EXEC?=docker-compose
MAIN?=python sutta_publisher

APP_PATH = sutta_publisher/src

PROD_DOCKER_COMPOSE=./docker-compose.yml
DEV_DOCKER_COMPOSE=./docker-compose.dev.yml

LINT_PATHS = $(APP_PATH)


##############################################################################
### Run app
###########
run:
	$(COMPOSE_EXEC) -f $(PROD_DOCKER_COMPOSE) run publisher $(MAIN) $(filter-out $@,$(MAKECMDGOALS))


run-dev:
	$(COMPOSE_EXEC) -f $(PROD_DOCKER_COMPOSE) -f $(DEV_DOCKER_COMPOSE) run publisher $(MAIN) $(filter-out $@,$(MAKECMDGOALS))


build:
	$(COMPOSE_EXEC) -f $(PROD_DOCKER_COMPOSE) build publisher


clean:
	$(COMPOSE_EXEC) -f $(PROD_DOCKER_COMPOSE) rm -fsv
	$(COMPOSE_EXEC) -f $(PROD_DOCKER_COMPOSE) -f $(DEV_DOCKER_COMPOSE) rm -fsv
##############################################################################


##############################################################################
### Testing
###########
build-dev:
	$(COMPOSE_EXEC) -f $(PROD_DOCKER_COMPOSE) -f $(DEV_DOCKER_COMPOSE) build publisher


test: build-dev
	$(COMPOSE_EXEC) -f $(PROD_DOCKER_COMPOSE) -f $(DEV_DOCKER_COMPOSE) run publisher pytest /tests


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
	$(PYTHON_EXEC) -m piptools compile --no-annotate --no-header --generate-hashes "${PROJ_ROOT}/sutta_publisher/dev.in"
	$(PYTHON_EXEC) -m piptools compile --no-annotate --no-header --generate-hashes "${PROJ_ROOT}/sutta_publisher/prod.in"


recompile-deps:
	$(PYTHON_EXEC) -m piptools compile --no-annotate --no-header --generate-hashes --upgrade "${PROJ_ROOT}/sutta_publisher/dev.in"
	$(PYTHON_EXEC) -m piptools compile --no-annotate --no-header --generate-hashes --upgrade "${PROJ_ROOT}/sutta_publisher/prod.in"


sync-deps:
	$(PYTHON_EXEC) -m piptools help >/dev/null 2>&1 || $(PYTHON_EXEC) -m pip install pip-tools
	$(PYTHON_EXEC) -m piptools sync "${PROJ_ROOT}/sutta_publisher/dev.txt"
	$(PYTHON_EXEC) -m pip install -e .


# Silent unused rules
%:
	@:

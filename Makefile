PROJ_ROOT=$(dir $(abspath $(lastword $(MAKEFILE_LIST))))
PYTHON_EXEC?=python
COMPOSE_EXEC?=docker-compose

APP_PATH = sutta_publisher/src
TESTS_PATH = sutta_publisher/tests

PROD_DOCKER_COMPOSE=./docker-compose.yml
DEV_DOCKER_COMPOSE=./docker-compose.dev.yml

LINT_PATHS = $(APP_PATH) $(TESTS_PATH)


##############################################################################
### Run app
###########
run:
	$(COMPOSE_EXEC) -f $(PROD_DOCKER_COMPOSE) run publisher python sutta_publisher $(filter-out $@,$(MAKECMDGOALS))

run-dev:
	$(COMPOSE_EXEC) -f $(PROD_DOCKER_COMPOSE) -f $(DEV_DOCKER_COMPOSE) run publisher python sutta_publisher $(filter-out $@,$(MAKECMDGOALS))

run-debug:
	$(COMPOSE_EXEC) -f $(PROD_DOCKER_COMPOSE) -f $(DEV_DOCKER_COMPOSE) run publisher python -m debugpy --wait-for-client --listen 0.0.0.0:5678 sutta_publisher $(filter-out $@,$(MAKECMDGOALS))

run-command:
	$(COMPOSE_EXEC) -f $(PROD_DOCKER_COMPOSE) -f $(DEV_DOCKER_COMPOSE) run publisher $(filter-out $@,$(MAKECMDGOALS))

build:
	$(COMPOSE_EXEC) -f $(PROD_DOCKER_COMPOSE) build publisher


clean:
	$(COMPOSE_EXEC) -f $(PROD_DOCKER_COMPOSE) rm -fsv
	$(COMPOSE_EXEC) -f $(PROD_DOCKER_COMPOSE) -f $(DEV_DOCKER_COMPOSE) rm -fsv


##############################################################################
### Testing
###########
build-dev:
	$(COMPOSE_EXEC) -f $(PROD_DOCKER_COMPOSE) -f $(DEV_DOCKER_COMPOSE) build publisher


test: build-dev
	$(COMPOSE_EXEC) -f $(PROD_DOCKER_COMPOSE) -f $(DEV_DOCKER_COMPOSE) run publisher pytest /tests

# TODO: [67] Reimplement using already defined `make lint` job and **in container**
test-ci: test


##############################################################################
### Dependency & linting
########################
lint:
	$(PYTHON_EXEC) -W ignore -m autoflake --in-place --recursive --ignore-init-module-imports --remove-duplicate-keys --remove-unused-variables --remove-all-unused-imports $(LINT_PATHS)
	$(PYTHON_EXEC) -m black $(LINT_PATHS)
	$(PYTHON_EXEC) -m isort $(LINT_PATHS)
	$(PYTHON_EXEC) -m mypy $(APP_PATH)
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

run-dev-all:
	$(COMPOSE_EXEC) -f $(PROD_DOCKER_COMPOSE) -f $(DEV_DOCKER_COMPOSE) run publisher python sutta_publisher scpub2 foo
	$(COMPOSE_EXEC) -f $(PROD_DOCKER_COMPOSE) -f $(DEV_DOCKER_COMPOSE) run publisher python sutta_publisher scpub7 foo
	$(COMPOSE_EXEC) -f $(PROD_DOCKER_COMPOSE) -f $(DEV_DOCKER_COMPOSE) run publisher python sutta_publisher scpub16 foo
	$(COMPOSE_EXEC) -f $(PROD_DOCKER_COMPOSE) -f $(DEV_DOCKER_COMPOSE) run publisher python sutta_publisher scpub17 foo
	$(COMPOSE_EXEC) -f $(PROD_DOCKER_COMPOSE) -f $(DEV_DOCKER_COMPOSE) run publisher python sutta_publisher scpub1 foo
	$(COMPOSE_EXEC) -f $(PROD_DOCKER_COMPOSE) -f $(DEV_DOCKER_COMPOSE) run publisher python sutta_publisher scpub6 foo
	$(COMPOSE_EXEC) -f $(PROD_DOCKER_COMPOSE) -f $(DEV_DOCKER_COMPOSE) run publisher python sutta_publisher scpub18 foo
	$(COMPOSE_EXEC) -f $(PROD_DOCKER_COMPOSE) -f $(DEV_DOCKER_COMPOSE) run publisher python sutta_publisher scpub3 foo
	$(COMPOSE_EXEC) -f $(PROD_DOCKER_COMPOSE) -f $(DEV_DOCKER_COMPOSE) run publisher python sutta_publisher scpub4 foo
	$(COMPOSE_EXEC) -f $(PROD_DOCKER_COMPOSE) -f $(DEV_DOCKER_COMPOSE) run publisher python sutta_publisher scpub5 foo
	$(COMPOSE_EXEC) -f $(PROD_DOCKER_COMPOSE) -f $(DEV_DOCKER_COMPOSE) run publisher python sutta_publisher scpub8 foo

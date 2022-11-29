PROJ_ROOT=$(dir $(abspath $(lastword $(MAKEFILE_LIST))))
PYTHON_EXEC?=python
COMPOSE_EXEC?=docker-compose
DOCKER_EXEC?=docker
GIT_EXEC?=git

IMAGE_NAME?=paccakkha/suttacentral
IMAGE_TARGET?=production
IMAGE_VERSION?=suttapublisher_$(IMAGE_TARGET)

APP_PATH?=sutta_publisher/src
TESTS_PATH?=sutta_publisher/tests

PROD_DOCKER_COMPOSE?=./docker-compose.yml
DEV_DOCKER_COMPOSE?=./docker-compose.dev.yml

LINT_PATHS?=$(APP_PATH) $(TESTS_PATH)

PUBLICATIONS_LIST?=scpub2 scpub7 scpub16 scpub17 scpub1 scpub6 scpub18 scpub3 scpub4 scpub5 scpub8


##############################################################################
### Run app
###########
run:
	$(COMPOSE_EXEC) -f $(PROD_DOCKER_COMPOSE) run publisher python sutta_publisher $(filter-out $@,$(MAKECMDGOALS))

run-dev:
	$(COMPOSE_EXEC) -f $(PROD_DOCKER_COMPOSE) -f $(DEV_DOCKER_COMPOSE) run publisher python sutta_publisher $(filter-out $@,$(MAKECMDGOALS))

run-dev-all:
	for publication in $(PUBLICATIONS_LIST) ; do \
		$(COMPOSE_EXEC) -f $(PROD_DOCKER_COMPOSE) -f $(DEV_DOCKER_COMPOSE) run publisher python sutta_publisher $(filter-out $@,$(MAKECMDGOALS)) $$publication; \
	done

run-debug:
	$(COMPOSE_EXEC) -f $(PROD_DOCKER_COMPOSE) -f $(DEV_DOCKER_COMPOSE) run publisher python -m debugpy --wait-for-client --listen 0.0.0.0:5678 sutta_publisher $(filter-out $@,$(MAKECMDGOALS))

run-command:
	$(COMPOSE_EXEC) -f $(PROD_DOCKER_COMPOSE) -f $(DEV_DOCKER_COMPOSE) run publisher $(filter-out $@,$(MAKECMDGOALS))

run-bash:
	$(COMPOSE_EXEC) -f $(PROD_DOCKER_COMPOSE) -f $(DEV_DOCKER_COMPOSE) run publisher bash

build:
	cd $(APP_PATH)/.. ; $(DOCKER_EXEC) build -t=$(IMAGE_NAME):$(IMAGE_VERSION) --target=$(IMAGE_TARGET) -f=Dockerfile ./

push-docker-image:
	$(DOCKER_EXEC)  push $(IMAGE_NAME):$(IMAGE_VERSION)

clean:
	$(COMPOSE_EXEC) -f $(PROD_DOCKER_COMPOSE) rm -fsv
	$(COMPOSE_EXEC) -f $(PROD_DOCKER_COMPOSE) -f $(DEV_DOCKER_COMPOSE) rm -fsv


##############################################################################
### Testing
###########

test:
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

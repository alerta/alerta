#!make

VENV=venv
PYTHON=$(VENV)/bin/python3
PIP=$(VENV)/bin/pip --disable-pip-version-check
FLAKE8=$(VENV)/bin/flake8
MYPY=$(VENV)/bin/mypy
TOX=$(VENV)/bin/tox
PYTEST=$(VENV)/bin/pytest
DOCKER_COMPOSE=docker-compose
PRE_COMMIT=$(VENV)/bin/pre-commit
BUILD=$(VENV)/bin/build
WHEEL=$(VENV)/bin/wheel
TWINE=$(VENV)/bin/twine
GIT=git

.DEFAULT_GOAL:=help

-include .env .env.local .env.*.local

ifndef PROJECT
    $(error PROJECT is not set)
endif

PYPI_REPOSITORY ?= pypi
VERSION=$(shell cut -d "'" -f 2 $(PROJECT)/version.py)

all:	help

$(VENV):
	python3 -m venv $(VENV)

$(FLAKE8): $(VENV)
	$(PIP) install flake8

$(MYPY): $(VENV)
	$(PIP) install mypy

$(TOX): $(VENV)
	$(PIP) install tox

$(PYTEST): $(VENV)
	$(PIP) install pytest pytest-cov

$(PRE_COMMIT): $(VENV)
	$(PIP) install pre-commit
	$(PRE_COMMIT) install

$(BUILD): $(VENV)
	$(PIP) install --upgrade build

$(WHEEL): $(VENV)
	$(PIP) install --upgrade wheel

$(TWINE): $(VENV)
	$(PIP) install --upgrade wheel twine

ifdef TOXENV
    toxparams?=-e $(TOXENV)
endif

## install		- Install dependencies.
install: $(VENV)
	$(PIP) install -r requirements.txt

## hooks			- Run pre-commit hooks.
hooks: $(PRE_COMMIT)
	$(PRE_COMMIT) run --all-files --show-diff-on-failure

## lint			- Lint and type checking.
lint: $(FLAKE8) $(MYPY)
	$(FLAKE8) $(PROJECT)/
	$(MYPY) $(PROJECT)/

## test			- Run all tests.
test: test.unit test.integration

## test.unit		- Run unit tests.
test.unit: $(TOX) $(PYTEST)
	$(TOX) $(toxparams)

## test.integration	- Run integration tests.
test.integration: test.integration.ldap test.integration.saml

test.integration.ldap: $(PYTEST)
	$(PIP) install -r requirements-ci.txt
	$(DOCKER_COMPOSE) -f docker-compose.ci.yml up -d
	$(PYTEST) tests/integration/test_auth_ldap.py $(toxparams)

test.integration.saml: $(PYTEST)
	$(PIP) install -r requirements-ci.txt
	$(DOCKER_COMPOSE) -f docker-compose.ci.yml up -d
	$(PYTEST) tests/integration/test_auth_saml.py $(toxparams)

## test.forwarder		- Run forwarder tests.
test.forwarder:
	$(DOCKER_COMPOSE) -f tests/integration/fixtures/docker-compose.yml pull
	$(DOCKER_COMPOSE) -f tests/integration/fixtures/docker-compose.yml up

## run			- Run application.
run:
	alertad

## tag			- Git tag with current version.
tag:
	$(GIT) tag -a v$(VERSION) -m "version $(VERSION)"
	$(GIT) push --tags

## build			- Build package.
build: $(BUILD)
	$(PYTHON) -m build

## upload			- Upload package to PyPI.
upload: $(TWINE)
	$(TWINE) check dist/*
	$(TWINE) upload --repository $(PYPI_REPOSITORY) --verbose dist/*

## clean			- Clean source.
clean:
	rm -rf $(VENV)
	rm -rf .tox
	rm -rf dist
	rm -rf build
	find . -name "*.pyc" -exec rm {} \;

## help			- Show this help.
help: Makefile
	@echo ''
	@echo 'Usage:'
	@echo '  make [TARGET]'
	@echo ''
	@echo 'Targets:'
	@sed -n 's/^##//p' $<
	@echo ''

	@echo 'Add project-specific env variables to .env file:'
	@echo 'PROJECT=$(PROJECT)'

.PHONY: help lint test build sdist wheel clean all

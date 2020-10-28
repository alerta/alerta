#!make

VENV=venv
PYTHON=$(VENV)/bin/python
PIP=$(VENV)/bin/pip --disable-pip-version-check
PYLINT=$(VENV)/bin/pylint
MYPY=$(VENV)/bin/mypy
BLACK=$(VENV)/bin/black
TOX=$(VENV)/bin/tox
PYTEST=$(VENV)/bin/pytest
DOCKER_COMPOSE=docker-compose
PRE_COMMIT=$(VENV)/bin/pre-commit
WHEEL=$(VENV)/bin/wheel
TWINE=$(VENV)/bin/twine
GIT=git

.DEFAULT_GOAL:=help

-include .env .env.local .env.*.local

ifndef PROJECT
$(error PROJECT is not set)
endif

VERSION=$(shell cut -d "'" -f 2 $(PROJECT)/version.py)

PKG_SDIST=dist/*-$(VERSION).tar.gz
PKG_WHEEL=dist/*-$(VERSION)-*.whl

all:	help

$(PIP):
	python3 -m venv $(VENV)

$(PYLINT): $(PIP)
	$(PIP) install pylint

$(MYPY): $(PIP)
	$(PIP) install mypy

$(BLACK): $(PIP)
	$(PIP) install black

$(TOX): $(PIP)
	$(PIP) install tox

$(PYTEST): $(PIP)
	$(PIP) install pytest

$(PRE_COMMIT): $(PIP)
	$(PIP) install pre-commit

$(WHEEL): $(PIP)
	$(PIP) install wheel

$(TWINE): $(PIP)
	$(PIP) install twine

ifdef TOXENV
toxparams?=-e $(TOXENV)
endif

## format			- Code formatter.
format: $(BLACK)
	$(BLACK) -l120 -S -v $(PROJECT)

## hooks			- Run pre-commit hooks.
hooks: $(PRE_COMMIT)
	$(PRE_COMMIT) run --all-files --show-diff-on-failure

## lint			- Lint and type checking.
lint: $(PYLINT) $(BLACK) $(MYPY)
	$(PYLINT) --rcfile pylintrc $(PROJECT)
	$(BLACK) -l120 -S --check -v $(PROJECT) || true
	$(MYPY) $(PROJECT)/

## test.unit		- Run unit tests.
test: test.unit
test.unit: $(TOX) $(PYTEST)
	$(TOX) $(toxparams)

## test.integration	- Run integration tests.
test.integration: $(PYTEST)
	$(DOCKER_COMPOSE) -f docker-compose.ci.yml up -d
	$(PYTEST) tests/integration

## run			- Run application.
run:
	alertad

## tag			- Git tag with current version.
tag:
	$(GIT) tag -a v$(VERSION) -m "version $(VERSION)"
	$(GIT) push --tags

## build			- Build package.
build: $(PIP) $(WHEEL) $(PKG_SDIST) $(PKG_WHEEL)

$(PKG_SDIST):
	$(PYTHON) setup.py sdist

$(PKG_WHEEL): $(WHEEL)
	$(PYTHON) setup.py bdist_wheel

## upload			- Upload package to PyPI.
upload: $(TWINE)
	$(TWINE) upload dist/*

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

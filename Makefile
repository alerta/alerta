#!make

VENV=venv
PYTHON=$(VENV)/bin/python
PIP=$(VENV)/bin/pip --disable-pip-version-check
FLAKE8=$(VENV)/bin/flake8
MYPY=$(VENV)/bin/mypy
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

$(FLAKE8): $(PIP)
	$(PIP) install flake8==4.0.1

$(MYPY): $(PIP)
	$(PIP) install mypy==0.812

$(TOX): $(PIP)
	$(PIP) install tox

$(PYTEST): $(PIP)
	$(PIP) install pytest==6.2.5 pytest-cov==3.0.0

$(PRE_COMMIT): $(PIP)
	$(PIP) install pre-commit==2.15.0
	$(PRE_COMMIT) install

$(WHEEL): $(PIP)
	$(PIP) install wheel

$(TWINE): $(PIP)
	$(PIP) install wheel twine

ifdef TOXENV
toxparams?=-e $(TOXENV)
endif

## install		- Install dependencies.
install: $(PIP)
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
test.integration: $(PYTEST)
	$(PIP) install -r requirements-ci.txt
	$(DOCKER_COMPOSE) -f docker-compose.ci.yml up -d
	$(PYTEST) tests/integration $(toxparams)

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

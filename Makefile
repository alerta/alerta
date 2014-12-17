
PYTHON=python
VERSION=`cat VERSION`

all:	help

help:
	@echo ""
	@echo "Usage: make <command>"
	@echo ""
	@echo "Commands:"
	@echo "   init    Initialise environment"
	@echo "   pylint  Lint source code"
	@echo "   test    Run tests"
	@echo ""

init:
	pip install -r requirements.txt

pylint:
	@pip -q install pylint
	pylint --rcfile pylintrc alerta

test:
	nosetests tests

run:
	alertad

git-tag:
	git tag -a v$(VERSION) -m "version $(VERSION)"

upload:
	$(PYTHON) setup.py sdist upload

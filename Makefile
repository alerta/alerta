
PYTHON=python
VERSION=`cut -d "'" -f 2 alerta/version.py`

all:	help

help:
	@echo ""
	@echo "Usage: make <command>"
	@echo ""
	@echo "Commands:"
	@echo "   init    Initialise environment"
	@echo "   dev     Initialise dev environment"
	@echo "   pylint  Lint source code"
	@echo "   mypy    Type checking"
	@echo "   clean   Clean source"
	@echo "   test    Run tests"
	@echo "   run     Run application"
	@echo "   tag     Git tag with current version"
	@echo "   upload  Upload package to PyPI"
	@echo ""

init:
	pip install -r requirements.txt --upgrade
	pip install -e .

dev:
	pip install -r requirements-dev.txt --upgrade
	pre-commit install
	pre-commit autoupdate

pylint:
	@pip -q install pylint
	pylint --rcfile pylintrc alerta

mypy:
	@pip -q install mypy==0.620
	mypy alerta/

hooks:
	pre-commit run --all-files

clean:
	find . -name "*.pyc" -exec rm {} \;
	rm -Rf build dist *.egg-info

test:
	ALERTA_SVR_CONF_FILE= pytest

run:
	alertad run --port 8080 --with-threads --reload

tag:
	git tag -a v$(VERSION) -m "version $(VERSION)"
	git push --tags

upload:
	$(PYTHON) setup.py sdist bdist_wheel
	twine upload dist/*

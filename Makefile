
PYTHON=python
VERSION=`cut -d "'" -f 2 alerta/version.py`

all:	help

help:
	@echo ""
	@echo "Usage: make <command>"
	@echo ""
	@echo "Commands:"
	@echo "   init    Initialise environment"
	@echo "   pylint  Lint source code"
	@echo "   clean   Clean source"
	@echo "   test    Run tests"
	@echo "   run     Run application"
	@echo "   tag     Git tag with current version"
	@echo "   upload  Upload package to PyPI"
	@echo ""

init:
	pip install -r requirements.txt --upgrade
	pip install -e .

pylint:
	@pip -q install pylint
	pylint --rcfile pylintrc alerta

clean:
	find . -name "*.pyc" -exec rm {} \;
	rm -Rf build dist *.egg-info

test:
	ALERTA_SVR_CONF_FILE= nosetests tests

run:
	alertad run --port 8080 --with-threads --reload

tag:
	git tag -a v$(VERSION) -m "version $(VERSION)"
	git push --tags

upload:
	$(PYTHON) setup.py sdist bdist_wheel upload

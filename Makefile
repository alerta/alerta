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

all: help

help:
    clear
    @echo ""
    @echo "Usage: make <command>"
    @echo ""
    @echo "Commands:"
    @echo "   init    Initialise environment"
    @echo "   pylint  Lint source code"
    @echo "   test    Run tests"
    @echo ""

init:
	pip install -r requirements.txt --use-mirrors

pylint:
    pylint --rcfile pylintrc alerta

test:
	nosetests tests
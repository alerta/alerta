
import click

from flask.cli import FlaskGroup

from alerta.app import create_app


def make_app(script_info):
    return create_app()


@click.group(cls=FlaskGroup, create_app=make_app)
def cli():
    """This is a development script for the Alerta server."""

if __name__ == '__main__':
    cli()

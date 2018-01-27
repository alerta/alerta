
import sys
import click

from flask import current_app
from flask.cli import FlaskGroup, with_appcontext

from alerta.app import create_app, db
from alerta.models.key import ApiKey


@click.group(cls=FlaskGroup, create_app=create_app)
def cli():
    pass


@cli.command()
@with_appcontext
def key():
    db.get_db()
    for admin in current_app.config['ADMIN_USERS']:
        key = ApiKey(
            user=admin,
            scopes=['admin', 'write', 'read'],
            text='Admin key created by alertad script',
            expire_time=None
        )
        try:
            key = key.create()
        except Exception as e:
            click.echo('ERROR: {}'.format(e))
            sys.exit(1)
        click.echo('{} {}'.format(key.key, key.user))

# @cli.command()
# @with_appcontext
# # @click.option('--coverage/--no-coverage', default=False, help='aaa')
# # def test(coverage=False):
# def test():
#     click.echo('test')


if __name__ == '__main__':
    cli()

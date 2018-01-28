
import sys

import click
from flask import current_app
from flask.cli import FlaskGroup, with_appcontext

from alerta.app import create_app, db
from alerta.auth.utils import generate_password_hash
from alerta.models.key import ApiKey
from alerta.models.user import User


@click.group(cls=FlaskGroup, create_app=create_app)
def cli():
    pass


@cli.command('key', short_help='Create admin API keys')
@with_appcontext
def key():
    """Create admin APi keys."""
    for admin in current_app.config['ADMIN_USERS']:
        key = ApiKey(
            user=admin,
            scopes=['admin', 'write', 'read'],
            text='Admin key created by alertad script',
            expire_time=None
        )
        try:
            db.get_db()  # init db on global app context
            key = key.create()
        except Exception as e:
            click.echo('ERROR: {}'.format(e))
        else:
            click.echo('{} {}'.format(key.key, key.user))


@cli.command('user', short_help='Create admin users')
@click.password_option()
@with_appcontext
def user(password):
    """Create admin users."""
    for admin in current_app.config['ADMIN_USERS']:
        user = User(
            name=admin,
            email=admin,
            password=generate_password_hash(password),
            roles=None,
            text='Admin user created by alertad script',
            email_verified=True
        )
        try:
            db.get_db()  # init db on global app context
            user = user.create()
        except Exception as e:
            click.echo('ERROR: {}'.format(e))
        else:
            click.echo('{} {}'.format(user.id, user.name))


if __name__ == '__main__':
    cli()


import click
from flask import current_app
from flask.cli import FlaskGroup, with_appcontext

from alerta.app import db
from alerta.auth.utils import generate_password_hash
from alerta.models.enums import Scope
from alerta.models.key import ApiKey
from alerta.models.user import User


def _create_app(info):
    from alerta.app import create_app
    return create_app()


@click.group(cls=FlaskGroup, create_app=_create_app)
def cli():
    pass


@cli.command('key', short_help='Create an admin API key')
@click.option('--username', '-u', help='Admin user')
@click.option('--key', '-K', help='API key (default=random UUID)')
@click.option('--all', is_flag=True, help='Create API keys for all admins')
@with_appcontext
def key(username, key, all):
    """Create an admin API key."""
    if username and username not in current_app.config['ADMIN_USERS']:
        raise click.UsageError('User {} not an admin'.format(username))

    def create_key(admin, key):
        key = ApiKey(
            user=admin,
            key=key,
            scopes=[Scope.admin, Scope.write, Scope.read],
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

    if all:
        for admin in current_app.config['ADMIN_USERS']:
            create_key(admin, key)
    elif username:
        create_key(username, key)
    else:
        raise click.UsageError("Must set '--username' or use '--all'")


@cli.command('keys', short_help='List admin API keys')
@with_appcontext
def keys():
    """List admin API keys."""
    for admin in current_app.config['ADMIN_USERS']:
        try:
            db.get_db()  # init db on global app context
            keys = ApiKey.find_by_user(admin)
        except Exception as e:
            click.echo('ERROR: {}'.format(e))
        else:
            for key in keys:
                click.echo('{:40} {}'.format(key.key, key.user))


@cli.command('user', short_help='Create admin user')
@click.option('--username', '-u', help='Admin user')
@click.password_option()
@click.option('--all', is_flag=True, help='Create users for all admins')
@with_appcontext
def user(username, password, all):
    """Create admin users (BasicAuth only)."""
    if current_app.config['AUTH_PROVIDER'] != 'basic':
        raise click.UsageError('Not required for {} admin users'.format(current_app.config['AUTH_PROVIDER']))
    if username and username not in current_app.config['ADMIN_USERS']:
        raise click.UsageError('User {} not an admin'.format(username))
    if not username and not all:
        raise click.UsageError('Missing option "--username".')

    def create_user(admin):
        email = admin if '@' in admin else None
        user = User(
            name='Admin user',
            login=admin,
            password=generate_password_hash(password),
            roles=['admin'],
            text='Created by alertad script',
            email=email,
            email_verified=bool(email)
        )
        try:
            db.get_db()  # init db on global app context
            user = user.create()
        except Exception as e:
            click.echo('ERROR: {}'.format(e))
        else:
            click.echo('{} {}'.format(user.id, user.name))

    if all:
        for admin in current_app.config['ADMIN_USERS']:
            create_user(admin)
    else:
        create_user(username)


@cli.command('users', short_help='List admin users')
@with_appcontext
def users():
    """List admin users."""
    for admin in current_app.config['ADMIN_USERS']:
        try:
            db.get_db()  # init db on global app context
            user = User.find_by_username(admin)
        except Exception as e:
            click.echo('ERROR: {}'.format(e))
        else:
            if user:
                click.echo('{} {}'.format(user.id, user.name))


if __name__ == '__main__':
    cli()

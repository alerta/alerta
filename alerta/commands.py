import sys
from datetime import datetime, timedelta
from typing import Any, Dict

import click
from flask import Flask, current_app
from flask.cli import FlaskGroup, ScriptInfo, with_appcontext

from alerta.app import config, create_app, db, key_helper, qb
from alerta.auth.utils import generate_password_hash
from alerta.models.enums import Scope
from alerta.models.key import ApiKey
from alerta.models.user import User
from alerta.version import __version__


def _create_app(config_override: Dict[str, Any] = None, environment: str = None) -> Flask:
    app = Flask(__name__)
    app.config['ENVIRONMENT'] = environment
    config.init_app(app)
    app.config.update(config_override or {})

    db.init_db(app)
    qb.init_app(app)
    key_helper.init_app(app)

    return app


@click.group(cls=FlaskGroup, add_version_option=False)
@click.version_option(version=__version__)
@click.pass_context
def cli(ctx):
    """
    Management command-line tool for Alerta server.
    """
    if ctx.invoked_subcommand in ['routes', 'run', 'shell']:
        # Load HTTP endpoints for standard Flask commands
        ctx.obj = ScriptInfo(create_app=create_app)
    else:
        # Do not load HTTP endpoints for management commands
        ctx.obj = ScriptInfo(create_app=_create_app)


@cli.command('key', short_help='Create an admin API key')
@click.option('--username', '-u', help='Admin user')
@click.option('--key', '-K', 'want_key', help='API key (default=random string)')
@click.option('--scope', 'scopes', multiple=True, help='List of permissions eg. admin:keys, write:alerts')
@click.option('--duration', metavar='SECONDS', type=int, help='Duration API key is valid')
@click.option('--text', help='Description of API key use')
@click.option('--customer', help='Customer')
@click.option('--all', is_flag=True, help='Create API keys for all admins')
@click.option('--force', is_flag=True, help='Do not skip if API key already exists')
@with_appcontext
def key(username, want_key, scopes, duration, text, customer, all, force):
    """
    Create an admin API key.
    """
    if username and username not in current_app.config['ADMIN_USERS']:
        raise click.UsageError('User {} not an admin'.format(username))

    if all and want_key:
        raise click.UsageError('Can only set API key with "--username".')

    scopes = [Scope(s) for s in scopes] or [Scope.admin, Scope.write, Scope.read]
    expires = datetime.utcnow() + timedelta(seconds=duration) if duration else None
    text = text or 'Created by alertad script'

    def create_key(admin, key=None):
        key = ApiKey(
            user=admin,
            key=key,
            scopes=scopes,
            expire_time=expires,
            text=text,
            customer=customer
        )
        try:
            key = key.create()
        except Exception as e:
            click.echo('ERROR: {}'.format(e))
        else:
            return key

    if all:
        for admin in current_app.config['ADMIN_USERS']:
            keys = [k for k in ApiKey.find_by_user(admin) if k.scopes == scopes]
            if keys and not force:
                key = keys[0]
            else:
                key = create_key(admin)
            click.echo('{:40} {}'.format(key.key, key.user))

    elif username:
        keys = [k for k in ApiKey.find_by_user(username) if k.scopes == scopes]
        if want_key:
            found_key = [k for k in keys if k.key == want_key]
            if found_key:
                key = found_key[0]
            else:
                key = create_key(username, key=want_key)
        else:
            if keys and not force:
                key = keys[0]
            else:
                key = create_key(username)
        if key:
            click.echo(key.key)
        else:
            sys.exit(1)

    else:
        raise click.UsageError("Must set '--username' or use '--all'")


@cli.command('keys', short_help='List admin API keys')
@with_appcontext
def keys():
    """
    List admin API keys.
    """
    for admin in current_app.config['ADMIN_USERS']:
        try:
            keys = [k for k in ApiKey.find_by_user(admin) if Scope.admin in k.scopes]
        except Exception as e:
            click.echo('ERROR: {}'.format(e))
        else:
            for key in keys:
                click.echo('{:40} {}'.format(key.key, key.user))


class CommandWithOptionalPassword(click.Command):

    def parse_args(self, ctx, args):
        for i, a in enumerate(args):
            if args[i] == '--password':
                try:
                    password = args[i + 1] if not args[i + 1].startswith('--') else None
                except IndexError:
                    password = None
                if not password:
                    password = click.prompt('Password', hide_input=True, confirmation_prompt=True)
                    args.insert(i + 1, password)
        return super().parse_args(ctx, args)


@cli.command('user', cls=CommandWithOptionalPassword, short_help='Create admin user')
@click.option('--name', help='Name of admin (default=email)')
@click.option('--email', '--username', help='Email address (login username)')
@click.option('--password', help='Password (will prompt if not supplied)')
@click.option('--text', help='Description of admin')
@click.option('--all', is_flag=True, help='Create users for all admins')
@with_appcontext
def user(name, email, password, text, all):
    """
    Create admin users (BasicAuth only).
    """
    if current_app.config['AUTH_PROVIDER'] != 'basic':
        raise click.UsageError('Not required for {} admin users'.format(current_app.config['AUTH_PROVIDER']))

    if email and email not in current_app.config['ADMIN_USERS']:
        raise click.UsageError('User {} not an admin'.format(email))
    if (email or all) and not password:
        password = click.prompt('Password', hide_input=True)

    text = text or 'Created by alertad script'

    def create_user(name, login):
        email = login if '@' in login else None
        user = User(
            name=name or login,
            login=login,
            password=generate_password_hash(password),
            roles=current_app.config['ADMIN_ROLES'],
            text=text,
            email=email,
            email_verified=bool(email)
        )
        try:
            user = user.create()
        except Exception as e:
            click.echo('ERROR: {}'.format(e))
        else:
            return user

    if all:
        for admin in current_app.config['ADMIN_USERS']:
            user = User.find_by_username(admin)
            if not user:
                user = create_user(name=admin, login=admin)
            click.echo('{} {}'.format(user.id, user.login))

    elif email:
        user = create_user(name, login=email)
        if user:
            click.echo(user.id)
        else:
            sys.exit(1)

    else:
        raise click.UsageError("Must set '--email' or use '--all'")


@cli.command('users', short_help='List admin users')
@with_appcontext
def users():
    """
    List admin users.
    """
    for admin in current_app.config['ADMIN_USERS']:
        try:
            user = User.find_by_username(admin)
        except Exception as e:
            click.echo('ERROR: {}'.format(e))
        else:
            if user:
                click.echo('{} {}'.format(user.id, user.login))

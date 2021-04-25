import contextlib
import json
import os
import unittest

from alerta.app import create_app, db


@contextlib.contextmanager
def mod_env(*remove, **update):
    """
    See https://stackoverflow.com/questions/2059482#34333710

    Temporarily updates the ``os.environ`` dictionary in-place.

    The ``os.environ`` dictionary is updated in-place so that the modification
    is sure to work in all situations.

    :param remove: Environment variables to remove.
    :param update: Dictionary of environment variables and values to add/update.
    """
    env = os.environ
    update = update or {}
    remove = remove or []

    # List of environment variables being updated or removed.
    stomped = (set(update.keys()) | set(remove)) & set(env.keys())
    # Environment variables and values to restore on exit.
    update_after = {k: env[k] for k in stomped}
    # Environment variables and values to remove on exit.
    remove_after = frozenset(k for k in update if k not in env)

    try:
        env.update(update)
        [env.pop(k, None) for k in remove]
        yield
    finally:
        env.update(update_after)
        [env.pop(k) for k in remove_after]


class ConfigTestCase(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        db.destroy()

    def test_config(self):

        test_config = {
            'TESTING': True,
            'AUTH_REQUIRED': True,
            'CUSTOMER_VIEWS': True,
            'PLUGINS': []
        }
        self.allowed_environments = ['Foo', 'Bar', 'Baz', 'QUUX']
        self.allowed_github_orgs = ['gh1', 'gh2']
        self.allowed_gitlab_groups = ['gl1', 'gl2']
        self.allowed_keycloak_roles = ['kc1', 'kc2']
        self.allowed_oidc_roles = ['oidc1', 'oidc2']

        with mod_env(
                ALLOWED_ENVIRONMENTS=','.join(self.allowed_environments),
                DEFAULT_ENVIRONMENT='Baz',
                ALLOWED_GITHUB_ORGS=','.join(self.allowed_github_orgs),
                # ALLOWED_GITLAB_GROUPS=','.join(self.allowed_gitlab_groups),
                ALLOWED_KEYCLOAK_ROLES=','.join(self.allowed_keycloak_roles),
                # ALLOWED_OIDC_ROLES=','.join(self.allowed_oidc_roles),
        ):

            self.app = create_app(test_config)
            self.client = self.app.test_client()

            response = self.client.get('/config')
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data.decode('utf-8'))

            self.assertTrue(data['auth_required'])
            self.assertTrue(data['customer_views'])
            self.assertListEqual(data['sort_by'], ['severity', 'lastReceiveTime'])
            self.assertEqual(data['environments'], self.allowed_environments)

            self.assertEqual(self.app.config['ALLOWED_GITHUB_ORGS'], self.allowed_github_orgs)
            # self.assertEqual(self.app.config['ALLOWED_GITLAB_GROUPS'], self.allowed_gitlab_groups)
            # self.assertEqual(self.app.config['ALLOWED_KEYCLOAK_ROLES'], self.allowed_keycloak_roles)
            self.assertEqual(self.app.config['ALLOWED_OIDC_ROLES'], self.allowed_keycloak_roles)

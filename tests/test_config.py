import json
import unittest

from alerta.app import create_app, db
from tests.helpers.utils import mod_env


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
        self.clipboard_template = """
        {% if status=='closed' %}This alert is closed:{% else %}This alert is open:{% endif %}
        [{{ environment | upper }}] {{ resource }}
        {{ text }}
        """

        with mod_env(
                ALLOWED_ENVIRONMENTS=','.join(self.allowed_environments),
                DEFAULT_ENVIRONMENT='Baz',
                ALLOWED_GITHUB_ORGS=','.join(self.allowed_github_orgs),
                # ALLOWED_GITLAB_GROUPS=','.join(self.allowed_gitlab_groups),
                ALLOWED_KEYCLOAK_ROLES=','.join(self.allowed_keycloak_roles),
                CLIPBOARD_TEMPLATE=self.clipboard_template
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
            self.assertEqual(data['clipboard_template'], self.clipboard_template)

            self.assertEqual(self.app.config['ALLOWED_GITHUB_ORGS'], self.allowed_github_orgs)
            # self.assertEqual(self.app.config['ALLOWED_GITLAB_GROUPS'], self.allowed_gitlab_groups)
            # self.assertEqual(self.app.config['ALLOWED_KEYCLOAK_ROLES'], self.allowed_keycloak_roles)
            self.assertEqual(self.app.config['ALLOWED_OIDC_ROLES'], self.allowed_keycloak_roles)
            self.assertEqual(self.app.config['CLIPBOARD_TEMPLATE'], self.clipboard_template)

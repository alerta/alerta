import json
import unittest

from alerta.app import create_app
from alerta.models.token import Jwt


class LDAPIntegrationTestCase(unittest.TestCase):

    def setUp(self):

        test_config = {
            'TESTING': True,
            'DEBUG': True,
            'AUTH_REQUIRED': False,
            'ADMIN_USERS': ['professor@planetexpress.com'],

            'AUTH_PROVIDER': 'ldap',
            'ALLOWED_EMAIL_DOMAINS': ['planetexpress.com'],
            'LDAP_URL': 'ldap://localhost:389',
            'LDAP_BASEDN': 'dc=planetexpress,dc=com',

            'LDAP_DOMAINS': {
                # 'planetexpress.com': 'cn=%s,ou=people,dc=planetexpress,dc=com',
            },

            'LDAP_BIND_USERNAME': 'cn=admin,dc=planetexpress,dc=com',
            'LDAP_BIND_PASSWORD': 'GoodNewsEveryone',

            'LDAP_USER_BASEDN': 'ou=people,dc=planetexpress,dc=com',
            'LDAP_USER_FILTER': '(&(uid={username})(objectClass=inetOrgPerson))',
            'LDAP_USER_NAME_ATTR': 'cn',
            'LDAP_USER_EMAIL_ATTR': 'mail',

            'LDAP_GROUP_BASEDN': 'ou=people,dc=planetexpress,dc=com',
            'LDAP_GROUP_FILTER': '(&(member={userdn})(objectClass=group))',
            'LDAP_GROUP_NAME_ATTR': 'cn',  # memberOf or cn

            'LDAP_DEFAULT_DOMAIN': 'planetexpress.com'
        }
        self.app = create_app(test_config)
        self.client = self.app.test_client()

    def test_login(self):

        payload = {
            'email': 'bender@planetexpress.com',
            'password': 'bender'
        }
        response = self.client.post('/auth/login', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIn('token', data)

        with self.app.test_request_context():
            jwt = Jwt.parse(data['token'])

        self.assertEqual(jwt.issuer, 'http://localhost/')
        self.assertEqual(jwt.name, 'Bender Bending Rodríguez')
        self.assertEqual(jwt.preferred_username, 'bender@planetexpress.com')
        self.assertEqual(jwt.email, 'bender@planetexpress.com')
        self.assertEqual(jwt.provider, 'ldap')
        self.assertEqual(jwt.orgs, [])
        self.assertEqual(jwt.groups, ['ship_crew'])
        self.assertEqual(jwt.roles, ['user'])
        self.assertEqual(jwt.scopes, ['read', 'write'])
        self.assertEqual(jwt.email_verified, True)
        self.assertEqual(jwt.picture, None)
        self.assertEqual(jwt.customers, [])

    def test_login_with_ldap_domain(self):

        payload = {
            'username': 'planetexpress.com\\leela',
            'password': 'leela'
        }
        response = self.client.post('/auth/login', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIn('token', data)

        with self.app.test_request_context():
            jwt = Jwt.parse(data['token'])

        self.assertEqual(jwt.issuer, 'http://localhost/')
        self.assertEqual(jwt.name, 'Turanga Leela')
        self.assertEqual(jwt.preferred_username, 'leela@planetexpress.com')
        self.assertEqual(jwt.email, 'leela@planetexpress.com')
        self.assertEqual(jwt.provider, 'ldap')
        self.assertEqual(jwt.orgs, [])
        self.assertEqual(jwt.groups, ['ship_crew'])
        self.assertEqual(jwt.roles, ['user'])
        self.assertEqual(jwt.scopes, ['read', 'write'])
        self.assertEqual(jwt.email_verified, True)
        self.assertEqual(jwt.picture, None)
        self.assertEqual(jwt.customers, [])

    def test_login_with_no_domain(self):

        payload = {
            'username': 'professor',
            'password': 'professor'
        }
        response = self.client.post('/auth/login', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIn('token', data)

        with self.app.test_request_context():
            jwt = Jwt.parse(data['token'])

        self.assertEqual(jwt.issuer, 'http://localhost/')
        self.assertEqual(jwt.name, 'Hubert J. Farnsworth')
        self.assertEqual(jwt.preferred_username, 'professor@planetexpress.com')
        self.assertEqual(jwt.email, 'professor@planetexpress.com')
        self.assertEqual(jwt.provider, 'ldap')
        self.assertEqual(jwt.orgs, [])
        self.assertEqual(jwt.groups, ['admin_staff'])
        self.assertEqual(jwt.roles, ['admin'])
        self.assertEqual(jwt.scopes, ['admin', 'read', 'write'])
        self.assertEqual(jwt.email_verified, True)
        self.assertEqual(jwt.picture, None)
        self.assertEqual(jwt.customers, [])

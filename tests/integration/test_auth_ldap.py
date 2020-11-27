import json
import unittest

from alerta.app import create_app
from alerta.models.token import Jwt


class LDAPIntegrationTestCase(unittest.TestCase):

    def setUp(self):

        test_config = {
            'TESTING': True,
            'DEBUG': False,
            'AUTH_REQUIRED': True,
            'ADMIN_USERS': ['professor@planetexpress.com'],

            'AUTH_PROVIDER': 'ldap',
            'ALLOWED_EMAIL_DOMAINS': ['planetexpress.com'],
            'LDAP_URL': 'ldap://localhost:389',
            'LDAP_TIMEOUT': 10,
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

            'LDAP_CONFIG': {
                'OPT_REFERRALS': 0,
                'OPT_PROTOCOL_VERSION': 3,
                'OPT_DEBUG_LEVEL': -1
            },
            # Scenario 1. default usage using group DN
            # 'LDAP_GROUP_FILTER': '(&(member={userdn})(objectClass=group))',
            # 'ALLOWED_LDAP_GROUPS': [
            #     'cn=admin_staff,ou=people,dc=planetexpress,dc=com',
            #     'cn=ship_crew,ou=people,dc=planetexpress,dc=com'
            # ],

            # Scenario 2. group cn is (short) group name
            # 'LDAP_GROUP_FILTER': '(&(member={userdn})(objectClass=group))',
            # 'LDAP_GROUP_NAME_ATTR': 'cn',
            # 'ALLOWED_LDAP_GROUPS': [
            #     'admin_staff',
            #     'ship_crew'
            # ],

            # Scenario 3. memberOf dn is used as group name
            'LDAP_GROUP_FILTER': '(&(uid={username})(objectClass=inetOrgPerson))',
            'LDAP_GROUP_NAME_ATTR': 'memberOf',
            'ALLOWED_LDAP_GROUPS': [
                'cn=admin_staff,ou=people,dc=planetexpress,dc=com',
                'cn=ship_crew,ou=people,dc=planetexpress,dc=com'
            ],

            'LDAP_DEFAULT_DOMAIN': 'planetexpress.com',
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
        self.assertEqual(jwt.groups, ['cn=ship_crew,ou=people,dc=planetexpress,dc=com'])
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
        self.assertEqual(jwt.groups, ['cn=ship_crew,ou=people,dc=planetexpress,dc=com'])
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
        self.assertEqual(jwt.groups, ['cn=admin_staff,ou=people,dc=planetexpress,dc=com'])
        self.assertEqual(jwt.roles, ['admin'])
        self.assertEqual(jwt.scopes, ['admin', 'read', 'write'])
        self.assertEqual(jwt.email_verified, True)
        self.assertEqual(jwt.picture, None)
        self.assertEqual(jwt.customers, [])

    def test_login_invalid_group(self):

        payload = {
            'username': 'zoidberg',
            'password': 'zoidberg'
        }
        response = self.client.post('/auth/login', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 403)

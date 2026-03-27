import unittest

import requests_mock

from alerta.app import create_app
from alerta.auth.cas import flatten_attrs, validate_cas


class CasAuthTestCase(unittest.TestCase):

    def setUp(self):
        config = {
            'TESTING': True,
            'AUTH_REQUIRED': True,
            'AUTH_PROVIDER': 'cas',
            'CAS_SERVER': 'https://cas.example.com'
        }
        self.app = create_app(config)

    def test_flatten_attrs(self):
        raw = {'a': ['b'], 'c': ['d', 'e'], 'f': 'g'}
        result = flatten_attrs(raw)
        self.assertEqual(result['a'], 'b')
        self.assertEqual(result['c'], ['d', 'e'])
        self.assertEqual(result['f'], 'g')

    @requests_mock.Mocker()
    def test_validate_cas_json_success(self, m):
        response = {
            'serviceResponse': {
                'authenticationSuccess': {
                    'user': 'jdoe',
                    'attributes': {
                        'mail': ['jdoe@example.com'],
                        'roles': ['user']
                    }
                }
            }
        }
        m.get(
            'https://cas.example.com/serviceValidate',
            json=response,
            headers={'Content-Type': 'application/json'}
        )
        with self.app.app_context():
            success, username, attrs, raw = validate_cas(
                'ST-1',
                'svc',
                self.app.config['CAS_SERVER']
            )
        self.assertTrue(success)
        self.assertEqual(username, 'jdoe')
        # flatten_attrs turns single-item lists into scalars
        self.assertEqual(attrs, {
            'mail': 'jdoe@example.com',
            'roles': 'user'
        })
        self.assertEqual(raw, response)

    @requests_mock.Mocker()
    def test_validate_cas_xml_success(self, m):
        xml = """<cas:serviceResponse xmlns:cas='http://www.yale.edu/tp/cas'>
  <cas:authenticationSuccess>
    <cas:user>jdoe</cas:user>
    <cas:attributes>
      <cas:mail>jdoe@example.com</cas:mail>
    </cas:attributes>
  </cas:authenticationSuccess>
</cas:serviceResponse>"""
        m.get(
            'https://cas.example.com/serviceValidate',
            text=xml,
            headers={'Content-Type': 'text/xml'}
        )
        with self.app.app_context():
            success, username, attrs, raw = validate_cas(
                'ST-2',
                'svc',
                self.app.config['CAS_SERVER']
            )
        self.assertTrue(success)
        self.assertEqual(username, 'jdoe')
        self.assertEqual(attrs, {'mail': 'jdoe@example.com'})
        self.assertEqual(raw.strip(), xml)

    @requests_mock.Mocker()
    def test_validate_cas_json_failure(self, m):
        failure = {
            'serviceResponse': {
                'authenticationFailure': {
                    'code': 'INVALID_TICKET',
                    'description': 'ticket not recognized'
                }
            }
        }
        m.get(
            'https://cas.example.com/serviceValidate',
            json=failure,
            headers={'Content-Type': 'application/json'}
        )
        with self.app.app_context():
            success, username, attrs, raw = validate_cas(
                'BAD',
                'svc',
                self.app.config['CAS_SERVER']
            )
        self.assertFalse(success)
        self.assertIsNone(username)
        self.assertEqual(attrs, {})
        self.assertEqual(raw, failure)


if __name__ == '__main__':
    unittest.main()

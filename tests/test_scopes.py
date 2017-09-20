
import json
import unittest

from alerta.app import create_app, db, key_helper
from alerta.models.key import ApiKey


class ScopeTestCase(unittest.TestCase):

    def setUp(self):

        test_config = {
            'TESTING': True,
            'AUTH_REQUIRED': True,
            'ADMIN_USERS': ['admin@alerta.io', 'sys@alerta.io']
        }
        self.app = create_app(test_config)
        self.client = self.app.test_client()

        def make_key(user, scopes=None, type=None, text=''):
            api_key = ApiKey(
                user=user,
                scopes=scopes,
                type=type,
                text=text
            )
            return api_key.create().key

        with self.app.test_request_context('/'):
            self.app.preprocess_request()
            self.api_keys_scopes = dict()
            self.api_keys_scopes['read-only'] = make_key('user@alerta.io', scopes=['read'], type=None, text='read-only')
            self.api_keys_scopes['read-write'] = make_key('user@alerta.io', scopes=['read', 'write'], type=None, text='read-write')
            self.api_keys_scopes['admin'] = make_key('admin@alerta.io', scopes=['read', 'write', 'admin'], type=None, text='admin')

            # self.api_keys_types = dict()
            # self.api_keys_types['read-only'] = make_key('user@alerta.io', scopes=None, type='read-only', text='read-only')
            # self.api_keys_types['read-write'] = make_key('user@alerta.io', scopes=None, type='read-write', text='read-write')
            # self.api_keys_types['admin'] = make_key('admin@alerta.io', scopes=None, type='read-write', text='admin')

    def tearDown(self):
        db.destroy()

    def test_scopes(self):

        response = self.client.get('/keys', headers={'Authorization': 'Key %s' % self.api_keys_scopes['read-only']})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        for key in data['keys']:
            self.assertEqual(self.api_keys_scopes[key['text']], key['key'])
            if key['text'] == 'admin':
                self.assertEqual('read-write', key['type'])
            else:
                self.assertEqual(key['text'], key['type'])
            self.assertEqual(sorted(key_helper.type_to_scopes(key['user'], key['text'])), sorted(key['scopes']))

    # def test_types(self):
    #     #FIXME
    #     response = self.client.get('/keys')
    #     self.assertEqual(response.status_code, 200)
    #     data = json.loads(response.data.decode('utf-8'))
    #     for key in data['keys']:
    #         self.assertEqual(self.api_keys_types[key['text']], key['key'])
    #         if key['text'] == 'admin':
    #             self.assertEqual('read-write', key['type'])
    #         else:
    #             self.assertEqual(key['text'], key['type'])
    #         self.assertEqual(sorted(key_helper.type_to_scopes(key['user'], key['text'])), sorted(key['scopes']))

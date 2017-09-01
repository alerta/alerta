
import unittest

from datetime import datetime, timedelta

try:
    import simplejson as json
except ImportError:
    import json

from alerta.app import create_app, db, key_helper


class ScopeTestCase(unittest.TestCase):

    def setUp(self):

        test_config = {
            'TESTING': True,
            'AUTH_REQUIRED': True,
            'ADMIN_USERS': ['admin@alerta.io', 'sys@alerta.io']
        }
        self.app = create_app(test_config)
        self.client = self.app.test_client()
        self.mongo = db

        """legacy keys admin, read-only, read-write
        1. insert directly into db
        2. create via API
        3. output and check both

        # new scoped keys admin, read-only, read-write
        """

        def make_key(user, scopes=None, type=None, text=''):
            data = {
                "_id": key_helper.generate(),
                "user": user,
                "text": text,
                "expireTime": datetime.utcnow() + timedelta(days=1),
                "count": 0,
                "lastUsedTime": None
            }
            if scopes:
                data['scopes'] = scopes
            if type:
                data['type'] = type

            self.mongo.db.keys.insert_one(data)
            return data['_id']

        with self.app.app_context():
            self.api_keys_scopes = dict()
            self.api_keys_scopes['read-only'] = make_key('user@alerta.io', scopes=['read'], type=None, text='read-only')
            self.api_keys_scopes['read-write'] = make_key('user@alerta.io', scopes=['read', 'write'], type=None, text='read-write')
            self.api_keys_scopes['admin'] = make_key('admin@alerta.io', scopes=['read', 'write', 'admin'], type=None, text='admin')

            # self.api_keys_types = dict()
            # self.api_keys_types['read-only'] = make_key('user@alerta.io', scopes=None, type='read-only', text='read-only')
            # self.api_keys_types['read-write'] = make_key('user@alerta.io', scopes=None, type='read-write', text='read-write')
            # self.api_keys_types['admin'] = make_key('admin@alerta.io', scopes=None, type='read-write', text='admin')

    def tearDown(self):
        with self.app.app_context():
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
    #
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

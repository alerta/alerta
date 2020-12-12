import json
import os
import unittest

from alerta.app import create_app, db


class ConfigTestCase(unittest.TestCase):

    def setUp(self):

        test_config = {
            'TESTING': True,
            'AUTH_REQUIRED': True,
            'CUSTOMER_VIEWS': True,
            'PLUGINS': []
        }
        self.allowed_environments = ['Foo', 'Bar', 'Baz', 'QUUX']
        os.environ['ALLOWED_ENVIRONMENTS'] = ','.join(self.allowed_environments)

        self.app = create_app(test_config)
        self.client = self.app.test_client()

    def tearDown(self):
        db.destroy()

    def test_config(self):

        response = self.client.get('/config')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))

        self.assertTrue(data['auth_required'])
        self.assertTrue(data['customer_views'])
        self.assertListEqual(data['sort_by'], ['severity', 'lastReceiveTime'])
        self.assertEqual(data['environments'], self.allowed_environments)

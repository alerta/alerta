import json
import unittest

import requests_mock

from alerta.app import create_app, db


class LoggingTestCase(unittest.TestCase):

    def setUp(self):

        test_config = {
            'TESTING': True,
            'AUTH_REQUIRED': False,
            'LOG_HANDLERS': ['console'],
            'LOG_FORMAT': 'verbose',
            'AUDIT_TRAIL': ['admin', 'write', 'auth'],
            'AUDIT_LOG': True,
            'AUDIT_LOG_JSON': True,
            'AUDIT_URL': 'https://logs.alerta.dev'
        }
        self.app = create_app(test_config)
        self.client = self.app.test_client()

    def tearDown(self):
        db.destroy()

    def test_audit_log(self):

        pass

    @requests_mock.mock()
    def test_audit_url(self, m):

        m.post('https://logs.alerta.dev')

        # create blackout
        response = self.client.post('/blackout', json={'environment': 'Production'})
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))

        blackout_id = data['id']

        # Note: The content_type header should not need to be set for deletes, but ...
        response = self.client.delete('/blackout/' + blackout_id, content_type='application/json')
        self.assertEqual(response.status_code, 200)

        create_blackout_request = json.loads(m.request_history[0].text)

        self.assertEqual(create_blackout_request['event'], 'blackout-created')
        self.assertEqual(create_blackout_request['category'], 'write')
        self.assertEqual(create_blackout_request['resource']['type'], 'blackout')
        self.assertEqual(create_blackout_request['request']['endpoint'], 'api.create_blackout')
        self.assertEqual(create_blackout_request['request']['method'], 'POST')
        self.assertEqual(create_blackout_request['request']['url'], 'http://localhost/blackout')
        self.assertEqual(create_blackout_request['request']['data'], {'environment': 'Production'})

        delete_blackout_request = json.loads(m.request_history[1].text)

        self.assertEqual(delete_blackout_request['event'], 'blackout-deleted')
        self.assertEqual(delete_blackout_request['category'], 'write')
        self.assertEqual(delete_blackout_request['resource']['type'], 'blackout')
        self.assertEqual(delete_blackout_request['request']['endpoint'], 'api.delete_blackout')
        self.assertEqual(delete_blackout_request['request']['method'], 'DELETE')
        self.assertTrue(delete_blackout_request['request']['url'].startswith('http://localhost/blackout/'))
        self.assertEqual(delete_blackout_request['request']['data'], None)
        self.assertTrue(delete_blackout_request['request']['userAgent'].startswith('Werkzeug/'), delete_blackout_request)

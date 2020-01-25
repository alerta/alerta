import unittest

from flask_cors import CORS
from flask_cors.extension import ACL_ALLOW_HEADERS, ACL_ORIGIN

from alerta.app import create_app, db


class HTTPCorsTestCase(unittest.TestCase):

    def setUp(self):

        test_config = {
            'TESTING': True,
            'AUTH_REQUIRED': False,
            'CORS_ORIGINS': ['http://localhost:5000', 'http://try.alerta.io'],
            'CORS_ALLOWED_HEADERS': ['Content-Type', 'Authorization', 'X-PING-PONG']
        }
        self.app = create_app(test_config)
        self.client = self.app.test_client()

        CORS(self.client.application, origins=self.app.config['CORS_ORIGINS'])

    def tearDown(self):

        db.destroy()

    def test_cors_headers(self):

        headers = {
            'Origin': 'http://try.alerta.io',
            'Access-Control-Request-Headers': 'authorization, content-type, X-XSRF-TOKEN',
            'Access-Control-Request-Method': 'GET'
        }

        # check Access-Control-Allow-Headers header
        response = self.client.options('/alerts', headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get(ACL_ALLOW_HEADERS), 'authorization, content-type')

        headers = {
            'Origin': 'http://try.alerta.io'
        }

        # check Access-Control-Allow-Origin header
        response = self.client.get('/alerts', headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get(ACL_ORIGIN), 'http://try.alerta.io')

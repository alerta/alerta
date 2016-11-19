
import unittest

try:
    import simplejson as json
except ImportError:
    import json

from flask_cors import CORS
from flask_cors.extension import ACL_ORIGIN, ACL_ALLOW_HEADERS

from alerta.app import app
from pymongo import MongoClient


class AlertTestCase(unittest.TestCase):

    def setUp(self):

        MongoClient().drop_database(app.config['MONGO_DATABASE'])

        app.config['TESTING'] = True
        app.config['AUTH_REQUIRED'] = False
        app.config['CORS_ORIGINS'] = ['http://localhost:5000', 'http://try.alerta.io']
        app.config['CORS_ALLOWED_HEADERS'] = ['Content-Type', 'Authorization', 'X-PING-PONG']
        self.app = app.test_client()
        CORS(self.app.application, origins=app.config['CORS_ORIGINS'])

    def tearDown(self):
        pass

    def test_cors_headers(self):

        headers = {
            'Origin': 'http://try.alerta.io',
            'Access-Control-Request-Headers': 'authorization, content-type, X-XSRF-TOKEN',
            'Access-Control-Request-Method': 'GET'
        }

        # check Access-Control-Allow-Headers header
        response = self.app.options('/alerts', headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get(ACL_ALLOW_HEADERS), 'authorization, content-type')

        headers = {
            'Origin': 'http://try.alerta.io'
        }

        # check Access-Control-Allow-Origin header
        response = self.app.get('/alerts', headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get(ACL_ORIGIN), 'http://try.alerta.io')

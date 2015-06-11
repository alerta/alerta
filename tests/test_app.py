
import unittest

from alerta.app import app


class AppTestCase(unittest.TestCase):

    def setUp(self):

        app.config['TESTING'] = True
        self.app = app.test_client()

    def tearDown(self):

        pass

    def test_debug_output(self):

        response = self.app.get('/_')
        self.assertEqual(response.status_code, 200)
        self.assertIn("ok", response.data)
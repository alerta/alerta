import json
import unittest

from alerta.app import app


class AppTestCase(unittest.TestCase):

    def setUp(self):

        app.config['TESTING'] = True
        app.config['AUTH_REQUIRED'] = False
        self.app = app.test_client()

        self.alert = {
            'event': 'Foo',
            'resource': 'Bar',
            'environment': 'Production',
            'service': ['Quux']
        }

    def tearDown(self):

        pass

    def test_debug_output(self):

        response = self.app.get('/_')
        self.assertEqual(response.status_code, 200)
        self.assertIn("ok", response.data)

    def test_new_alert(self):

        response = self.app.post('/alert', data=json.dumps(self.alert), headers={'Content-type': 'application/json'})
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertListEqual(self.alert['service'], data['alert']['service'])

        new_alert_id = data['id']

        response = self.app.get('/alert/' + new_alert_id)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn(new_alert_id, data['alert']['id'])

    def test_alert_not_found(self):

        response = self.app.get('/alert/doesnotexist')
        self.assertEqual(response.status_code, 404)

    def test_get_alerts(self):

        response = self.app.get('/alerts')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertGreater(data['total'], 1, "total alerts > 1")

    def test_alert_status(self):

        pass

    def test_alert_tagging(self):

        pass

    def test_delete_alert(self):

        pass

    def test_get_counts(self):

        pass

    def test_top10_alerts(self):

        pass

    def test_environments(self):

        pass

    def test_services(self):

        pass

    def test_heartbeats(self):

        pass

    def test_users(self):

        pass



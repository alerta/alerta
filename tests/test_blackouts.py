
import json
import unittest

from alerta.app import create_app, db, plugins
from alerta.exceptions import BlackoutPeriod
from alerta.models.key import ApiKey
from alerta.plugins import PluginBase


class BlackoutsTestCase(unittest.TestCase):

    def setUp(self):
        test_config = {
            'TESTING': True,
            'AUTH_REQUIRED': True,
            'CUSTOMER_VIEWS': True,
            'PLUGINS': ['reject']
        }
        self.app = create_app(test_config)
        self.client = self.app.test_client()

        self.alert = {
            'event': 'node_marginal',
            'resource': 'node404',
            'environment': 'Production',
            'service': ['Network'],
            'severity': 'warning',
            'correlate': ['node_down', 'node_marginal', 'node_up']
        }

        with self.app.test_request_context('/'):
            self.app.preprocess_request()
            self.admin_api_key = ApiKey(
                user='admin',
                scopes=['admin', 'read', 'write'],
                text='demo-key'
            )
            self.customer_api_key = ApiKey(
                user='admin',
                scopes=['admin', 'read', 'write'],
                text='demo-key',
                customer='Foo'
            )
            self.admin_api_key.create()
            self.customer_api_key.create()

    def tearDown(self):
        db.destroy()

    def test_suppress_blackout(self):

        plugins.plugins['blackout'] = SuppressionBlackout()

        self.headers = {
            'Authorization': 'Key %s' % self.admin_api_key.key,
            'Content-type': 'application/json'
        }

        # create alert
        response = self.client.post('/alert', data=json.dumps(self.alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)

        # create blackout
        response = self.client.post('/blackout', data=json.dumps({"environment": "Production"}), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))

        blackout_id = data['id']

        # suppress alert
        response = self.client.post('/alert', data=json.dumps(self.alert), headers=self.headers)
        self.assertEqual(response.status_code, 202)

        self.headers = {
            'Authorization': 'Key %s' % self.customer_api_key.key,
            'Content-type': 'application/json'
        }

        # create alert
        response = self.client.post('/alert', data=json.dumps(self.alert), headers=self.headers)
        self.assertEqual(response.status_code, 202)


        self.headers = {
            'Authorization': 'Key %s' % self.admin_api_key.key,
            'Content-type': 'application/json'
        }

        response = self.client.delete('/blackout/' + blackout_id, headers=self.headers)
        self.assertEqual(response.status_code, 200)

    def test_notification_blackout(self):

        plugins.plugins['blackout'] = NotificationBlackout()

        self.headers = {
            'Authorization': 'Key %s' % self.admin_api_key.key,
            'Content-type': 'application/json'
        }

        # create new blackout
        response = self.client.post('/blackout', data=json.dumps({"environment": "Production", "service": ["Network"]}), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))

        blackout_id = data['id']

        # new alert should be status=blackout
        response = self.client.post('/alert', data=json.dumps(self.alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'blackout')

        # duplicate alert should be status=blackout
        response = self.client.post('/alert', data=json.dumps(self.alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'blackout')

        # duplicate alert should be status=blackout (again)
        response = self.client.post('/alert', data=json.dumps(self.alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'blackout')

        # increase severity alert should be status=blackout
        self.alert['severity'] = 'major'
        response = self.client.post('/alert', data=json.dumps(self.alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'blackout')

        # increase severity alert should be status=blackout (again)
        self.alert['severity'] = 'critical'
        response = self.client.post('/alert', data=json.dumps(self.alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'blackout')

        # decrease severity alert should be status=blackout
        self.alert['severity'] = 'minor'
        response = self.client.post('/alert', data=json.dumps(self.alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'blackout')

        # decrease severity alert should be status=blackout (again)
        self.alert['severity'] = 'warning'
        response = self.client.post('/alert', data=json.dumps(self.alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'blackout')

        # normal severity alert should be status=closed
        self.alert['severity'] = 'ok'
        response = self.client.post('/alert', data=json.dumps(self.alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'closed')

        # normal severity alert should be status=closed (again)
        response = self.client.post('/alert', data=json.dumps(self.alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'closed')

        # non-normal severity alert should be status=blackout (again)
        self.alert['severity'] = 'major'
        response = self.client.post('/alert', data=json.dumps(self.alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'blackout')

        # decrease severity alert should be status=blackout
        self.alert['severity'] = 'minor'
        response = self.client.post('/alert', data=json.dumps(self.alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'blackout')

        # remove blackout
        response = self.client.delete('/blackout/' + blackout_id, headers=self.headers)
        self.assertEqual(response.status_code, 200)

        # normal severity alert should be status=closed
        self.alert['severity'] = 'ok'
        response = self.client.post('/alert', data=json.dumps(self.alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'closed')


class SuppressionBlackout(PluginBase):

    def pre_receive(self, alert):
        if alert.is_blackout():
            raise BlackoutPeriod("Suppressed alert during blackout period")
        return alert

    def post_receive(self, alert):
        return alert

    def status_change(self, alert, status, text):
        return


class NotificationBlackout(PluginBase):

    def pre_receive(self, alert):
        if alert.is_blackout():
            alert.status = 'blackout'
        return alert

    def post_receive(self, alert):
        return alert

    def status_change(self, alert, status, text):
        return

import json
import os
import unittest
from datetime import datetime

from alerta.app import create_app, db, plugins
from alerta.exceptions import BlackoutPeriod
from alerta.models.key import ApiKey
from alerta.plugins import PluginBase
from alerta.utils.format import DateTime


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

        self.prod_alert = {
            'resource': 'node404',
            'event': 'node_down',
            'environment': 'Production',
            'severity': 'major',
            'correlate': ['node_down', 'node_marginal', 'node_up'],
            'service': ['Core', 'Web', 'Network'],
            'group': 'Network',
            'tags': ['level=20', 'switch:off']
        }

        self.dev_alert = {
            'resource': 'node404',
            'event': 'node_marginal',
            'environment': 'Development',
            'severity': 'warning',
            'correlate': ['node_down', 'node_marginal', 'node_up'],
            'service': ['Core', 'Web', 'Network'],
            'group': 'Network',
            'tags': ['level=20', 'switch:off']
        }

        self.fatal_alert = {
            'event': 'node_down',
            'resource': 'net01',
            'environment': 'Production',
            'service': ['Network'],
            'severity': 'critical',
            'correlate': ['node_down', 'node_marginal', 'node_up'],
            'tags': ['foo'],
            'attributes': {'foo': 'abc def', 'bar': 1234, 'baz': False},
        }
        self.critical_alert = {
            'event': 'node_marginal',
            'resource': 'net02',
            'environment': 'Production',
            'service': ['Network'],
            'severity': 'critical',
            'correlate': ['node_down', 'node_marginal', 'node_up'],
            'timeout': 30
        }
        self.major_alert = {
            'event': 'node_marginal',
            'resource': 'net03',
            'environment': 'Production',
            'service': ['Network'],
            'severity': 'major',
            'correlate': ['node_down', 'node_marginal', 'node_up'],
            'timeout': 40
        }
        self.normal_alert = {
            'event': 'node_up',
            'resource': 'net03',
            'environment': 'Production',
            'service': ['Network'],
            'severity': 'normal',
            'correlate': ['node_down', 'node_marginal', 'node_up'],
            'timeout': 100
        }
        self.minor_alert = {
            'event': 'node_marginal',
            'resource': 'net04',
            'environment': 'Production',
            'service': ['Network'],
            'severity': 'minor',
            'correlate': ['node_down', 'node_marginal', 'node_up'],
            'timeout': 40
        }
        self.ok_alert = {
            'event': 'node_up',
            'resource': 'net04',
            'environment': 'Production',
            'service': ['Network'],
            'severity': 'ok',
            'correlate': ['node_down', 'node_marginal', 'node_up'],
            'timeout': 100
        }
        self.warn_alert = {
            'event': 'node_marginal',
            'resource': 'net05',
            'environment': 'Production',
            'service': ['Network'],
            'severity': 'warning',
            'correlate': ['node_down', 'node_marginal', 'node_up'],
            'timeout': 50
        }

        with self.app.test_request_context('/'):
            self.app.preprocess_request()
            self.admin_api_key = ApiKey(
                user='admin@alerta.io',
                scopes=['admin', 'read', 'write'],
                text='demo-key'
            )
            self.customer_api_key = ApiKey(
                user='admin@alerta.io',
                scopes=['admin', 'read', 'write'],
                text='demo-key',
                customer='Foo'
            )
            self.admin_api_key.create()
            self.customer_api_key.create()

    def tearDown(self):
        db.destroy()

    def test_suppress_blackout(self):

        os.environ['NOTIFICATION_BLACKOUT'] = 'False'
        plugins.plugins['blackout'] = Blackout()

        self.headers = {
            'Authorization': 'Key %s' % self.admin_api_key.key,
            'Content-type': 'application/json'
        }

        # create alert
        response = self.client.post('/alert', data=json.dumps(self.prod_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)

        # create blackout
        response = self.client.post('/blackout', data=json.dumps({'environment': 'Production'}), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))

        blackout_id = data['id']

        # suppress alert
        response = self.client.post('/alert', data=json.dumps(self.prod_alert), headers=self.headers)
        self.assertEqual(response.status_code, 202)

        self.headers = {
            'Authorization': 'Key %s' % self.customer_api_key.key,
            'Content-type': 'application/json'
        }

        # create alert
        response = self.client.post('/alert', data=json.dumps(self.prod_alert), headers=self.headers)
        self.assertEqual(response.status_code, 202)

        self.headers = {
            'Authorization': 'Key %s' % self.admin_api_key.key,
            'Content-type': 'application/json'
        }

        response = self.client.delete('/blackout/' + blackout_id, headers=self.headers)
        self.assertEqual(response.status_code, 200)

    def test_notification_blackout(self):

        os.environ['NOTIFICATION_BLACKOUT'] = 'True'
        plugins.plugins['blackout'] = Blackout()

        self.headers = {
            'Authorization': 'Key %s' % self.admin_api_key.key,
            'Content-type': 'application/json'
        }

        # create new blackout
        blackout = {
            'environment': 'Production',
            'service': ['Core']
        }
        response = self.client.post('/blackout', data=json.dumps(blackout), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))

        blackout_id = data['id']

        # new alert should be status=blackout
        response = self.client.post('/alert', data=json.dumps(self.prod_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'blackout')

        # duplicate alert should be status=blackout
        response = self.client.post('/alert', data=json.dumps(self.prod_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'blackout')

        # duplicate alert should be status=blackout (again)
        response = self.client.post('/alert', data=json.dumps(self.prod_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'blackout')

        # increase severity alert should be status=blackout
        self.prod_alert['severity'] = 'major'
        response = self.client.post('/alert', data=json.dumps(self.prod_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'blackout')

        # increase severity alert should be status=blackout (again)
        self.prod_alert['severity'] = 'critical'
        response = self.client.post('/alert', data=json.dumps(self.prod_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'blackout')

        # decrease severity alert should be status=blackout
        self.prod_alert['severity'] = 'minor'
        response = self.client.post('/alert', data=json.dumps(self.prod_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'blackout')

        # decrease severity alert should be status=blackout (again)
        self.prod_alert['severity'] = 'warning'
        response = self.client.post('/alert', data=json.dumps(self.prod_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'blackout')

        # normal severity alert should be status=closed
        self.prod_alert['severity'] = 'ok'
        response = self.client.post('/alert', data=json.dumps(self.prod_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'closed')

        # normal severity alert should be status=closed (again)
        response = self.client.post('/alert', data=json.dumps(self.prod_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'closed')

        # non-normal severity alert should be status=blackout (again)
        self.prod_alert['severity'] = 'major'
        response = self.client.post('/alert', data=json.dumps(self.prod_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'blackout')

        # decrease severity alert should be status=blackout
        self.prod_alert['severity'] = 'minor'
        response = self.client.post('/alert', data=json.dumps(self.prod_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'blackout')

        # remove blackout
        response = self.client.delete('/blackout/' + blackout_id, headers=self.headers)
        self.assertEqual(response.status_code, 200)

        # non-normal severity alert should be status=open
        self.prod_alert['severity'] = 'minor'
        response = self.client.post('/alert', data=json.dumps(self.prod_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'open')

        # normal severity alert should be status=closed
        self.prod_alert['severity'] = 'ok'
        response = self.client.post('/alert', data=json.dumps(self.prod_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'closed')

    def test_previous_status(self):

        self.headers = {
            'Authorization': 'Key %s' % self.admin_api_key.key,
            'Content-type': 'application/json'
        }

        # create an alert => critical, open
        response = self.client.post('/alert', data=json.dumps(self.fatal_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['severity'], 'critical')
        self.assertEqual(data['alert']['status'], 'open')

        alert_id_1 = data['id']

        # ack the alert => critical, ack
        response = self.client.put('/alert/' + alert_id_1 + '/action',
                                   data=json.dumps({'action': 'ack'}), headers=self.headers)
        self.assertEqual(response.status_code, 200)

        response = self.client.get('/alert/' + alert_id_1, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['severity'], 'critical')
        self.assertEqual(data['alert']['status'], 'ack')

        # create 2nd alert => critical, open
        response = self.client.post('/alert', data=json.dumps(self.critical_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['severity'], 'critical')
        self.assertEqual(data['alert']['status'], 'open')

        alert_id_2 = data['id']

        # shelve 2nd alert => critical, shelved
        response = self.client.put('/alert/' + alert_id_2 + '/action',
                                   data=json.dumps({'action': 'shelve'}), headers=self.headers)
        self.assertEqual(response.status_code, 200)

        response = self.client.get('/alert/' + alert_id_2, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['severity'], 'critical')
        self.assertEqual(data['alert']['status'], 'shelved')

        # create a blackout
        os.environ['NOTIFICATION_BLACKOUT'] = 'yes'
        plugins.plugins['blackout'] = Blackout()

        blackout = {
            'environment': 'Production',
            'service': ['Network']
        }
        response = self.client.post('/blackout', data=json.dumps(blackout), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))

        blackout_id = data['id']

        # update 1st alert => critical, blackout
        response = self.client.post('/alert', data=json.dumps(self.fatal_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['severity'], 'critical')
        self.assertEqual(data['alert']['status'], 'blackout')

        # create 3rd alert => major, blackout
        response = self.client.post('/alert', data=json.dumps(self.major_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['severity'], 'major')
        self.assertEqual(data['alert']['status'], 'blackout')

        # clear 3rd alert => normal, closed
        response = self.client.post('/alert', data=json.dumps(self.normal_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['severity'], 'normal')
        self.assertEqual(data['alert']['status'], 'closed')

        # create 4th alert => minor, blackout
        response = self.client.post('/alert', data=json.dumps(self.minor_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['severity'], 'minor')
        self.assertEqual(data['alert']['status'], 'blackout')

        # clear 4th alert => ok, closed
        response = self.client.post('/alert', data=json.dumps(self.ok_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['severity'], 'ok')
        self.assertEqual(data['alert']['status'], 'closed')

        # create 5th alert => warning, blackout
        response = self.client.post('/alert', data=json.dumps(self.warn_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['severity'], 'warning')
        self.assertEqual(data['alert']['status'], 'blackout')

        # remove blackout
        response = self.client.delete('/blackout/' + blackout_id, headers=self.headers)
        self.assertEqual(response.status_code, 200)

        # update 1st alert => critical, ack
        response = self.client.post('/alert', data=json.dumps(self.fatal_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['severity'], 'critical')
        self.assertEqual(data['alert']['status'], 'ack')

        # update 2nd alert => critical, shelved
        response = self.client.post('/alert', data=json.dumps(self.critical_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['severity'], 'critical')
        self.assertEqual(data['alert']['status'], 'shelved')

        # update 3rd alert => normal, closed
        response = self.client.post('/alert', data=json.dumps(self.normal_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['severity'], 'normal')
        self.assertEqual(data['alert']['status'], 'closed')

        # update 4th alert => minor, open
        response = self.client.post('/alert', data=json.dumps(self.minor_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['severity'], 'minor')
        self.assertEqual(data['alert']['status'], 'open')

        # update 5th alert => warning, open
        response = self.client.post('/alert', data=json.dumps(self.warn_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['severity'], 'warning')
        self.assertEqual(data['alert']['status'], 'open')

    def test_whole_environment_blackout(self):

        os.environ['NOTIFICATION_BLACKOUT'] = 'False'
        plugins.plugins['blackout'] = Blackout()

        self.headers = {
            'Authorization': 'Key %s' % self.admin_api_key.key,
            'Content-type': 'application/json'
        }

        # create alert
        response = self.client.post('/alert', data=json.dumps(self.dev_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)

        # create blackout (for whole development environment)
        blackout = {
            'environment': 'Development'
        }
        response = self.client.post('/blackout', data=json.dumps(blackout), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))

        blackout_id = data['id']

        # do not suppress production alert
        response = self.client.post('/alert', data=json.dumps(self.prod_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)

        # suppress development alert
        response = self.client.post('/alert', data=json.dumps(self.dev_alert), headers=self.headers)
        self.assertEqual(response.status_code, 202)

        # remove blackout
        response = self.client.delete('/blackout/' + blackout_id, headers=self.headers)
        self.assertEqual(response.status_code, 200)

        # do not suppress any alerts
        response = self.client.post('/alert', data=json.dumps(self.prod_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)

        response = self.client.post('/alert', data=json.dumps(self.dev_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)

    def test_combination_blackout(self):

        os.environ['NOTIFICATION_BLACKOUT'] = 'False'
        plugins.plugins['blackout'] = Blackout()

        self.headers = {
            'Authorization': 'Key %s' % self.admin_api_key.key,
            'Content-type': 'application/json'
        }

        # create alert
        response = self.client.post('/alert', data=json.dumps(self.prod_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)

        # create blackout (only for services on a particular host)
        blackout = {
            'environment': 'Production',
            'resource': 'node404',
            'service': ['Network', 'Web']
        }
        response = self.client.post('/blackout', data=json.dumps(blackout), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))

        blackout_id = data['id']

        # suppress alert
        response = self.client.post('/alert', data=json.dumps(self.prod_alert), headers=self.headers)
        self.assertEqual(response.status_code, 202)

        # remove blackout
        response = self.client.delete('/blackout/' + blackout_id, headers=self.headers)
        self.assertEqual(response.status_code, 200)

        # create alert
        response = self.client.post('/alert', data=json.dumps(self.prod_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)

        # create blackout (only for groups of alerts with particular tags)
        blackout = {
            'environment': 'Production',
            'group': 'Network',
            'tags': ['system:web01', 'switch:off']
        }
        response = self.client.post('/blackout', data=json.dumps(blackout), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))

        blackout_id = data['id']

        # do not suppress alert
        response = self.client.post('/alert', data=json.dumps(self.prod_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)

        self.prod_alert['tags'].append('system:web01')

        # suppress alert
        response = self.client.post('/alert', data=json.dumps(self.prod_alert), headers=self.headers)
        self.assertEqual(response.status_code, 202)

        # remove blackout
        response = self.client.delete('/blackout/' + blackout_id, headers=self.headers)
        self.assertEqual(response.status_code, 200)

        # create alert
        response = self.client.post('/alert', data=json.dumps(self.dev_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)

        # create blackout (only for resources with a particular tag)
        blackout = {
            'environment': 'Development',
            'resource': 'node404',
            'tags': ['level=40']
        }
        response = self.client.post('/blackout', data=json.dumps(blackout), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))

        blackout_id = data['id']

        # do not suppress alert
        response = self.client.post('/alert', data=json.dumps(self.dev_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)

        self.dev_alert['tags'].append('level=40')

        # suppress alert
        response = self.client.post('/alert', data=json.dumps(self.dev_alert), headers=self.headers)
        self.assertEqual(response.status_code, 202)

        # remove blackout
        response = self.client.delete('/blackout/' + blackout_id, headers=self.headers)
        self.assertEqual(response.status_code, 200)

    def test_edit_blackout(self):

        # create new blackout
        os.environ['NOTIFICATION_BLACKOUT'] = 'False'
        plugins.plugins['blackout'] = Blackout()

        self.headers = {
            'Authorization': 'Key %s' % self.admin_api_key.key,
            'Content-type': 'application/json'
        }

        # create alert
        response = self.client.post('/alert', data=json.dumps(self.prod_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)

        # create blackout (only for services on a particular host)
        blackout = {
            'environment': 'Production',
            'resource': 'node404',
            'service': ['Network', 'Web'],
            'startTime': '2019-01-01T00:00:00.000Z',
            'endTime': '2049-12-31T23:59:59.999Z'
        }
        response = self.client.post('/blackout', data=json.dumps(blackout), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))

        blackout_id = data['id']

        # suppress alert
        response = self.client.post('/alert', data=json.dumps(self.prod_alert), headers=self.headers)
        self.assertEqual(response.status_code, 202)

        # extend blackout period & change environment
        update = {
            'environment': 'Development',
            'event': None,
            'tags': [],
            'endTime': '2099-12-31T23:59:59.999Z'
        }
        response = self.client.put('/blackout/' + blackout_id, data=json.dumps(update), headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['status'], 'ok')

        # check updates worked and didn't change anything else
        response = self.client.get('/blackout/' + blackout_id, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['blackout']['environment'], 'Development')
        self.assertEqual(data['blackout']['resource'], 'node404')
        self.assertEqual(data['blackout']['service'], ['Network', 'Web'])
        self.assertEqual(data['blackout']['group'], None)
        self.assertEqual(data['blackout']['startTime'], '2019-01-01T00:00:00.000Z')
        self.assertEqual(data['blackout']['endTime'], '2099-12-31T23:59:59.999Z')

        # suppress alert
        response = self.client.post('/alert', data=json.dumps(self.dev_alert), headers=self.headers)
        self.assertEqual(response.status_code, 202)

    def test_user_info(self):

        self.headers = {
            'Authorization': 'Key %s' % self.admin_api_key.key,
            'Content-type': 'application/json'
        }

        # create new blackout
        response = self.client.post('/blackout', data=json.dumps({'environment': 'Production', 'service': [
                                    'Network'], 'text': 'administratively down'}), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['blackout']['user'], 'admin@alerta.io')
        self.assertIsInstance(DateTime.parse(data['blackout']['createTime']), datetime)
        self.assertEqual(data['blackout']['text'], 'administratively down')


class Blackout(PluginBase):

    def pre_receive(self, alert, **kwargs):
        NOTIFICATION_BLACKOUT = self.get_config('NOTIFICATION_BLACKOUT', default=True, type=bool, **kwargs)

        if alert.is_blackout():
            if NOTIFICATION_BLACKOUT:
                alert.status = 'blackout'
            else:
                raise BlackoutPeriod('Suppressed alert during blackout period')
        return alert

    def post_receive(self, alert, **kwargs):
        return alert

    def status_change(self, alert, status, text, **kwargs):
        return

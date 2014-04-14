
import json
import urllib
import requests

from alerta.common import log as logging
from alerta.common import config

__version__ = '3.0.4'

LOG = logging.getLogger(__name__)
CONF = config.CONF


class ApiClient(object):

    api_opts = {
        'endpoint': 'http://localhost:8080'
    }

    def __init__(self, endpoint=None):

        config.register_opts(ApiClient.api_opts)

        self.endpoint = endpoint or CONF.endpoint

    def __repr__(self):

        return 'ApiClient(endpoint=%r)' % self.endpoint

    def get_alerts(self, **kwargs):

        return self._get('/api/alerts', kwargs)

    def get_history(self, **kwargs):

        return self._get('/api/alerts/history', kwargs)

    def send_alert(self, alert):

        return self._post('/api/alert', data=str(alert))

    def send(self, msg):

        if msg.event_type == 'Heartbeat':
            return self.send_heartbeat(msg)
        else:
            return self.send_alert(msg)

    def get_alert(self, alertid):

        return self._get('/api/alert/%s' % alertid)

    def tag_alert(self, alertid, tags):

        if not isinstance(tags, list):
            raise

        return self._post('/api/alert/%s/tag' % alertid, data=json.dumps({"tags": tags}))

    def open_alert(self, alertid):

        self.update_status(alertid, 'open')

    def ack_alert(self, alertid):

        self.update_status(alertid, 'ack')

    def unack_alert(self, alertid):

        self.open_alert(alertid)

    def assign_alert(self, alertid):

        self.update_status(alertid, 'assigned')

    def close_alert(self, alertid):

        self.update_status(alertid, 'closed')

    def update_status(self, alertid, status):

        return self._post('/api/alert/%s/status' % alertid, data=json.dumps({"status": status}))

    def delete_alert(self, alertid):

        return self._delete('/api/alert/%s' % alertid)

    def send_heartbeat(self, heartbeat):
        """
        Send a heartbeat
        """
        return self._post('/api/heartbeat', data=str(heartbeat))

    def get_heartbeats(self):
        """
        Get list of heartbeats
        """
        return self._get('/api/heartbeats')

    def delete_heartbeat(self, heartbeatid):

        return self._delete('/api/heartbeat/%s' % heartbeatid)

    def _get(self, path, query=None):

        url = self.endpoint + path + '?' + urllib.urlencode(query, doseq=True)
        response = requests.get(url)

        LOG.debug('Content type from response: %s', response.headers['content-type'])
        LOG.debug('Response Headers: %s', response.headers)
        LOG.debug('Response Body: %s', response.text)

        try:
            response.raise_for_status()
        except requests.HTTPError:
            raise

        return response.json()

    def _post(self, path, data=None):

        url = self.endpoint + path
        headers = {'Content-Type': 'application/json'}

        LOG.debug('Request Headers: %s', headers)
        LOG.debug('Request Body: %s', data)

        response = requests.post(url, data=data, headers=headers)

        try:
            response.raise_for_status()
        except requests.HTTPError:
            raise

        return response.json()

    def _delete(self, path):

        url = self.endpoint + path
        response = requests.delete(url)

        try:
            response.raise_for_status()
        except requests.HTTPError:
            raise

        return response.json()

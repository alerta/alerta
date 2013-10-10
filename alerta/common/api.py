
import sys
import json
import requests

from alerta.common import log as logging
from alerta.common import config
from alerta.common.utils import DateEncoder

Version = '2.0.5'

LOG = logging.getLogger(__name__)
CONF = config.CONF


class ApiClient(object):

    def __init__(self, host=None, port=None, version='v2'):

        self.host = host or CONF.api_host
        self.port = port or CONF.api_port
        self.version = version or CONF.api_version

    def send(self, msg):


        LOG.debug('header = %s', msg.get_header())
        LOG.debug('message = %s', msg.get_body())

        if msg.get_type().endswith('Alert'):
            self.url = 'http://%s:%s/alerta/api/%s/alerts/alert.json' % (self.host, self.port, self.version)
        elif msg.get_type() == 'Heartbeat':
            self.url = 'http://%s:%s/alerta/api/%s/heartbeats/heartbeat.json' % (self.host, self.port, self.version)
        else:
            LOG.error('Message type %s not supported by this API endpoint.', msg.get_type())
            raise

        payload = json.dumps(msg.get_body(), ensure_ascii=False, cls=DateEncoder)
        headers = {'Content-Type': 'application/json'}

        if CONF.dry_run:
            print "curl -v '%s' -H 'Content-Type: application/json' -d '%s'" % (self.url, payload)
            sys.exit(0)

        LOG.debug('Sending alert to API endpoint...')
        try:
            r = requests.post(self.url, data=payload, headers=headers)
        except requests.Timeout, e:
            LOG.warning('API request timed out: %s', e)
            raise
        except requests.ConnectionError, e:
            LOG.error('API request connection error: %s', e)
            raise
        except requests.TooManyRedirects, e:
            LOG.error('Too many redirects: %s', e)
            raise
        except requests.RequestException, e:
            LOG.error('API request send failed: %s', e)
            raise

        LOG.debug('HTTP status: %s', r.status_code)
        LOG.debug('HTTP response: %s', r.text)

        try:
            r.raise_for_status()
        except requests.HTTPError, e:
            LOG.error('API request HTTP error: %s', e)
            raise

        try:
            response = r.json()['response']
        except Exception, e:
            LOG.error('API bad response - %s: %s', e, r.text)
            raise

        if response.get('status', None) == 'ok':
            LOG.debug('API request successful: %s', response)
            return response['id']
        elif response.get('status', None) == 'error' and 'message' in response:
            LOG.error('API request failed: %s', response['message'])
            raise
        else:
            LOG.error('API request unknown error: %s', response)
            raise



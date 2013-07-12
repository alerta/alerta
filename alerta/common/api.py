
import sys
import json
import urllib2


from alerta.common import log as logging
from alerta.common import config
from alerta.common.utils import DateEncoder

Version = '2.0.2'

LOG = logging.getLogger(__name__)
CONF = config.CONF

_API_TIMEOUT = 2  # seconds


class ApiClient(object):

    def send(self, msg, host=None, port=None, endpoint=None, dry_run=False):

        self.api_host = host or CONF.api_host
        self.api_port = port or CONF.api_port
        self.api_endpoint = endpoint or CONF.api_endpoint

        LOG.debug('header = %s', msg.get_header())
        LOG.debug('message = %s', msg.get_body())

        if msg.get_type().endswith('Alert'):
            api_url = 'http://%s:%s%s/alerts/alert.json' % (self.api_host, self.api_port, self.api_endpoint)
        elif msg.get_type() == 'Heartbeat':
            api_url = 'http://%s:%s%s/heartbeats/heartbeat.json' % (self.api_host, self.api_port, self.api_endpoint)
        else:
            LOG.error('Message type %s not supported by this API endpoint.', msg.get_type())
            return

        post = json.dumps(msg.get_body(), ensure_ascii=False, cls=DateEncoder)
        headers = {'Content-Type': 'application/json'}

        request = urllib2.Request(api_url, headers=headers)
        request.add_data(post)
        LOG.debug('url=%s, data=%s, headers=%s', request.get_full_url(), request.data, request.headers)

        if dry_run:
            print "curl '%s' -H 'Content-Type: application/json' -d '%s'" % (api_url, post)
            return

        LOG.debug('Sending alert to API endpoint...')
        try:
            response = urllib2.urlopen(request, post, _API_TIMEOUT)
        except ValueError, e:
            LOG.error('Could not send alert to API endpoint %s : %s', api_url, e)
            print >>sys.stderr, 'Could not send alert to API endpoint %s : status=%s' % (api_url, e)
            sys.exit(1)
        except urllib2.URLError, e:
            if hasattr(e, 'reason'):
                error = str(e.reason)
            elif hasattr(e, 'code'):
                error = e.code
            else:
                error = 'Unknown Send Error'
            LOG.error('Could not send to API endpoint %s : %s', api_url, error)
            print >>sys.stderr, 'Could not send to API endpoint %s : status=%s' % (api_url, error)
            sys.exit(2)
        else:
            code = response.getcode()
        LOG.info('Alert sent to API endpoint %s : status=%s', api_url, code)

        try:
            data = json.loads(response.read())
        except Exception, e:
            LOG.error('Error with response from API endpoint %s : %s', api_url, e)
            sys.exit(3)

        LOG.debug('Response from API endpoint: %s', data)

        response = data['response']
        if response.get('status', None) == 'ok':
            LOG.info('Response from API endpoint %s: %s', api_url, response)
            return response['id']
        elif response.get('status', None) == 'error' and 'message' in response:
            LOG.error('Error with response from API endpoint %s : %s', api_url, response['message'])
            sys.exit(4)
        else:
            LOG.error('Error with response from API endpoint %s : Unknown Receive Error', api_url)
            sys.exit(5)



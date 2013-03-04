
import time
import json
import urllib2
import datetime

from alerta.common import log as logging
from alerta.common import config

from alerta.common.daemon import Daemon
from alerta.common.mq import Messaging, MessageHandler
from alerta.alert import Alert, Heartbeat
from alerta.common.utils import DateEncoder

Version = '2.0.0'

LOG = logging.getLogger(__name__)
CONF = config.CONF


class LoggerDaemon(Daemon):
    """
    Index alerts in ElasticSearch using Logstash format so that logstash GUI and/or Kibana can be used as front-ends
    """
    def run(self):

        self.running = True

        # Connect to message queue
        self.mq = Messaging()
        self.mq.connect(callback=LoggerMessage())
        self.mq.subscribe(destination=CONF.outbound_queue)

        while not self.shuttingdown:
            try:
                LOG.debug('Waiting for log messages...')
                time.sleep(CONF.heartbeat_every)

                LOG.debug('Send heartbeat...')
                heartbeat = Heartbeat(version=Version)
                self.mq.send(heartbeat)

            except (KeyboardInterrupt, SystemExit):
                self.shuttingdown = True

        LOG.info('Shutdown request received...')
        self.running = False

        LOG.info('Disconnecting from message broker...')
        self.mq.disconnect()


class LoggerMessage(MessageHandler):
    
    def on_message(self, headers, body):

        LOG.debug("Received: %s", body)

        alert = Alert.parse_alert(body).get_body()
        if alert:

            LOG.info('%s : [%s] %s', alert['lastReceiveId'], alert['status'], alert['summary'])

            # TODO(nsatterl): is this still required?
            if 'tags' not in alert or not alert['tags']:           # Kibana GUI borks if tags are null
                alert['tags'] = 'none'

            LOG.debug('alert last receivetime %s', alert['lastReceiveTime'])

            logstash = {
                '@message': alert['summary'],
                '@source': alert['resource'],
                '@source_host': 'not_used',
                '@source_path': alert['origin'],
                '@tags': alert['tags'],
                '@timestamp': json.dumps(alert['lastReceiveTime'], cls=DateEncoder),
                '@type': alert['type'],
                '@fields': str(alert)
            }
            LOG.debug('Index payload %s', logstash)

            index_url = "http://%s:%s/alerta/%s" % (CONF.es_host, CONF.es_port,
                                                    'alerta-' + datetime.datetime.utcnow().strftime('%Y.%M.%d'))
            LOG.debug('Index URL: %s', index_url)

            try:
                response = urllib2.urlopen(index_url, json.dumps(logstash)).read()
            except Exception, e:
                LOG.error('%s : Alert indexing to %s failed - %s', alert['lastReceiveId'], index_url, e)
                return

            try:
                es_id = json.loads(response)['_id']
                LOG.info('%s : Alert indexed at %s/%s', alert['lastReceiveId'], index_url, es_id)
            except Exception:
                pass

import time
import json
import urllib2
import datetime

from alerta.common import log as logging
from alerta.common import config

from alerta.common.daemon import Daemon
from alerta.common.mq import Messaging, MessageHandler
from alerta.common.alert import Alert
from alerta.common.heartbeat import Heartbeat
from alerta.common.utils import DateEncoder

Version = '2.0.0'

LOG = logging.getLogger(__name__)
CONF = config.CONF


class LoggerMessage(MessageHandler):
    def __init__(self, mq):
        self.mq = mq
        MessageHandler.__init__(self)

    def on_message(self, headers, body):

        LOG.debug("Received: %s", body)
        alert = Alert.parse_alert(body).get_body()

        if alert:
            LOG.info('%s : [%s] %s', alert['lastReceiveId'], alert['status'], alert['summary'])

            source_host, _, source_path = alert['resource'].partition(':')
            document = {
                '@message': alert['summary'],
                '@source': alert['resource'],
                '@source_host': source_host,
                '@source_path': source_path,
                '@tags': alert['tags'],
                '@timestamp': alert['lastReceiveTime'],
                '@type': alert['type'],
                '@fields': alert
            }
            LOG.debug('Index payload %s', document)

            index_url = "http://%s:%s/%s/%s" % (CONF.es_host, CONF.es_port,
                                                datetime.datetime.utcnow().strftime(CONF.es_index), alert['type'])
            LOG.debug('Index URL: %s', index_url)

            try:
                response = urllib2.urlopen(index_url, json.dumps(document, cls=DateEncoder)).read()
            except Exception, e:
                LOG.error('%s : Alert indexing to %s failed - %s', alert['lastReceiveId'], index_url, e)
                return

            try:
                es_id = json.loads(response)['_id']
                LOG.info('%s : Alert indexed at %s/%s', alert['lastReceiveId'], index_url, es_id)
            except Exception, e:
                LOG.error('%s : Could not parse elasticsearch reponse: %s', e)

    def on_disconnected(self):
        self.mq.reconnect()


class LoggerDaemon(Daemon):
    """
    Index alerts in ElasticSearch using Logstash format so that logstash GUI and/or Kibana can be used as front-ends
    """

    def run(self):

        self.running = True

        # Connect to message queue
        self.mq = Messaging()
        self.mq.connect(callback=LoggerMessage(self.mq))
        self.mq.subscribe(destination=CONF.outbound_queue)

        while not self.shuttingdown:
            try:
                LOG.debug('Waiting for log messages...')
                time.sleep(CONF.loop_every)

                LOG.debug('Send heartbeat...')
                heartbeat = Heartbeat(version=Version)
                self.mq.send(heartbeat)

            except (KeyboardInterrupt, SystemExit):
                self.shuttingdown = True

        LOG.info('Shutdown request received...')
        self.running = False

        LOG.info('Disconnecting from message broker...')
        self.mq.disconnect()
import sys
import time
import json
from Queue import Queue

from dynect.DynectDNS import DynectRest

from alerta.common import config
from alerta.common import log as logging
from alerta.common.daemon import Daemon
from alerta.alert import Alert, Heartbeat
from alerta.common.mq import Messaging

Version = '2.0.0'

LOG = logging.getLogger(__name__)
CONF = config.CONF


class DynectDaemon(Daemon):
    def __init__(self, prog):

        Daemon.__init__(self, prog)

        self.info = {}
        self.last_info = {}
        self.count = 0
        self.updating = False

    def run(self):

        self.running = True

        # Connect to message queue
        self.mq = Messaging()
        self.mq.connect()

        while not self.shuttingdown:
            try:
                self.last_info = self.info

                self.queryDynect()
                self.alertDynect()

                if self.updating:
                    LOG.debug('Send heartbeat...')
                    heartbeat = Heartbeat(version=Version)
                    self.mq.send(heartbeat)

                LOG.debug('Waiting for next check run...')
                time.sleep(CONF.loop_every)
            except (KeyboardInterrupt, SystemExit):
                self.shuttingdown = True

        self.running = False

    def alertDynect(self):

        for resource in self.info:

            if self.last_info[resource]['status'] != self.info[resource]['status'] or self.count == 10:

                LOG.debug('Info => %s', resource)

                if resource.startswith('gslb-'):

                    # gslb status       = ok | unk | trouble | failover

                    LOG.info('GSLB state change from %s to %s' % (self.info[resource][0], self.last_self.info[resource][0]))
                    text = 'GSLB status is %s.' % self.last_info[resource][0]

                    if 'ok' in self.info[resource][0]:
                        event = 'GslbOK'
                        severity = 'NORMAL'
                    else:
                        event = 'GslbNotOK'
                        severity = 'CRITICAL'
                    correlate = ['GslbOK', 'GslbNotOK']

                elif resource.startswith('pool-'):

                    # pool status       = up | unk | down
                    # pool serve_mode   = obey | always | remove | no
                    # pool weight	(1-15)

                    LOG.info('Pool state change from %s to %s' % (self.info[resource][0], self.last_info[resource][0]))

                    if 'up:obey' in self.info[resource][0] and self.check_weight(self.info[resource][1], resource) == True:
                        event = 'PoolUp'
                        severity = 'NORMAL'
                        text = 'Pool status is normal'
                    else:
                        if 'down' in self.info[resource][0]:
                            event = 'PoolDown'
                            severity = 'MAJOR'
                            text = 'Pool is down'
                        elif 'obey' not in self.info[resource][0]:
                            event = 'PoolServe'
                            severity = 'MAJOR'
                            text = 'Pool with an incorrect serve mode'
                        elif self.check_weight(self.info[resource][1], resource) == False:
                            event = 'PoolWeightError'
                            severity = 'MINOR'
                            text = 'Pool with an incorrect weight'
                    correlate = ['PoolUp', 'PoolDown', 'PoolServe', 'PoolWeightError']

                # Defaults
                group = 'GSLB'
                value = self.info[resource][0]
                environment = ['PROD']
                service = ['Network']
                tags = list()
                timeout = None
                threshold_info = None
                summary = None

                dynectAlert = Alert(
                    resource=resource,
                    event=event,
                    correlate=correlate,
                    group=group,
                    value=value,
                    severity=severity,
                    environment=environment,
                    service=service,
                    text=text,
                    event_type='dynectAlert',
                    tags=tags,
                    timeout=timeout,
                    threshold_info=threshold_info,
                    summary=summary,
                    raw_data=None,
                )

                self.mq.send(dynectAlert)

        if self.count:
            self.count -= 1
        else:
            self.count = 10


    def check_weight(self, parent, resource):
        
        weight = self.info[resource][0].split(':')[2]
        for resource in self.info:
            if (resource.startswith('pool-') and self.info[resource][1] == parent and resource != resource and weight ==
                    self.info[resource][0].split(':')[2]):
                return True
        return False

    def queryDynect(self):

        LOG.info('Query DynECT to get the state of GSLBs')
        try:
            rest_iface = DynectRest()
            if CONF.debug and CONF.use_stderr:
                rest_iface.verbose = True

            credentials = {
                'customer_name': CONF.dynect_customer,
                'user_name': CONF.dynect_username,
                'password': CONF.dynect_password,
            }
            LOG.debug('credentials = %s', credentials)
            response = rest_iface.execute('/Session/', 'POST', credentials)

            if response['status'] != 'success':
                LOG.error('Failed to create API session: %s', response['msgs'][0]['INFO'])
                self.updating = False
                return

            # Discover all the Zones in DynECT
            response = rest_iface.execute('/Zone/', 'GET')
            LOG.debug('/Zone/ => %s', json.dumps(response, indent=4))
            zone_resources = response['data']

            # Discover all the LoadBalancers
            for resource in zone_resources:
                zone = resource.split('/')[3]  # eg. /REST/Zone/guardiannews.com/
                response = rest_iface.execute('/LoadBalance/' + zone + '/', 'GET')
                LOG.debug('/LoadBalance/%s/ => %s', zone, json.dumps(response, indent=4))
                gslb = response['data']

                # Discover LoadBalancer pool information.
                for lb in gslb:
                    fqdn = lb.split('/')[4]  # eg. /REST/LoadBalance/guardiannews.com/id.guardiannews.com/
                    response = rest_iface.execute('/LoadBalance/' + zone + '/' + fqdn + '/', 'GET')
                    LOG.debug('/LoadBalance/%s/%s/ => %s', zone, fqdn, json.dumps(response, indent=4))
                    self.info['gslb-' + fqdn] = {'status': response['data']['status'], 'gslb': fqdn}

                    for pool in response['data']['pool']:
                        name = '%s-%s' % (fqdn, pool['label'].replace(' ', '-'))
                        status = '%s:%s:%s' % (pool['status'], pool['serve_mode'], pool['weight'])
                        self.info['pool-' + name] = {'status': status, 'gslb': fqdn, 'rawData': pool}

            LOG.info('Finish quering and object discovery.')
            LOG.info('GSLBs and Pools: %s', json.dumps(self.info, indent=4))

            rest_iface.execute('/Session/', 'DELETE')

        except Exception, e:
            LOG.error('Failed to discover GSLBs: %s', e)
            self.updating = False

        self.updating = True





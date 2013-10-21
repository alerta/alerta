
import os
import sys
import urllib2
import json
import time
import yaml

import boto.ec2

from alerta.common import config
from alerta.common import log as logging
from alerta.common.daemon import Daemon
from alerta.common.alert import Alert
from alerta.common.heartbeat import Heartbeat
from alerta.common.alert import severity_code, status_code
from alerta.common.dedup import DeDup
from alerta.common.mq import Messaging, MessageHandler

Version = '2.0.5'

LOG = logging.getLogger(__name__)
CONF = config.CONF


class AwsMessage(MessageHandler):

    def __init__(self, mq):
        self.mq = mq
        MessageHandler.__init__(self)

    def on_disconnected(self):
        self.mq.reconnect()


class AwsDaemon(Daemon):

    aws_opts = {
        'fog_file': '/etc/fog/alerta.conf',
        'ec2_regions': ['eu-west-1', 'us-east-1'],
        'http_proxy': None,
        'https_proxy': None,
    }

    def __init__(self, prog, **kwargs):

        config.register_opts(AwsDaemon.aws_opts)
        
        Daemon.__init__(self, prog, kwargs)

        self.info = {}
        self.last = {}
        self.lookup = {}
        self.dedup = DeDup()

    def run(self):

        self.running = True

        # Read in FOG config file
        try:
            self.fog = yaml.load(open(CONF.fog_file).read())
        except IOError, e:
            LOG.error('Could not read AWS credentials file %s: %s', CONF.fog_file, e)
            sys.exit(1)

        if not self.fog:
            LOG.error('No AWS credentials found in FOG file %s. Exiting...', CONF.fog_file)
            sys.exit(1)

        # Connect to message queue
        self.mq = Messaging()
        self.mq.connect(callback=AwsMessage(self.mq))

        if CONF.http_proxy:
            os.environ['http_proxy'] = CONF.http_proxy
        if CONF.https_proxy:
            os.environ['https_proxy'] = CONF.https_proxy
        
        while not self.shuttingdown:
            try:
                self.ec2_status_check()

                LOG.debug('Send heartbeat...')
                heartbeat = Heartbeat(version=Version)
                self.mq.send(heartbeat)

                LOG.debug('Waiting for next check run...')
                time.sleep(CONF.loop_every)
            except (KeyboardInterrupt, SystemExit):
                self.shuttingdown = True

        LOG.info('Shutdown request received...')
        self.running = False

        LOG.info('Disconnecting from message broker...')
        self.mq.disconnect()

    def ec2_status_check(self):

        self.last = self.info.copy()
        self.info = {}

        for account, credential in self.fog.iteritems():
            account = account[1:]
            aws_access_key = credential.get(':aws_access_key_id', None)
            aws_secret_key = credential.get(':aws_secret_access_key', None)
            if not aws_access_key or not aws_secret_key:
                LOG.error('Invalid FOG credentials for %s, either access key or secret key missing' % account)
                sys.exit(1)

            for region in CONF.ec2_regions:
                try:
                    ec2 = boto.ec2.connect_to_region(
                        region,
                        aws_access_key_id=aws_access_key,
                        aws_secret_access_key=aws_secret_key
                    )
                except boto.exception.EC2ResponseError, e:
                    LOG.warning('EC2 API call connect_to_region(region=%s) failed: %s', region, e)
                    continue

                LOG.info('Get all instances for account %s in %s', account, region)
                try:
                    reservations = ec2.get_all_instances()
                except boto.exception.EC2ResponseError, e:
                    LOG.warning('EC2 API call get_all_instances() failed: %s', e)
                    continue

                instances = [i for r in reservations for i in r.instances if i.tags]
                for i in instances:
                    self.info[i.id] = dict()
                    self.info[i.id]['state'] = i.state
                    self.info[i.id]['stage'] = i.tags.get('Stage', 'unknown')
                    self.info[i.id]['role'] = i.tags.get('Role', 'unknown')
                    self.info[i.id]['tags'] = ['os:Linux', 'role:%s' % self.info[i.id]['role'], 'datacentre:%s' % region,
                                               'virtual:xen', 'cloud:AWS/EC2', 'account:%s' % account]
                    self.info[i.id]['tags'].append('cluster:%s_%s' % (self.info[i.id]['role'], region)) # FIXME - replace match on cluster with match on role

                    # FIXME - this is a hack until all EC2 instances are keyed off instance id
                    LOG.debug('%s -> %s', i.private_dns_name, i.id)
                    self.lookup[i.private_dns_name.split('.')[0]] = i.id

                LOG.info('Get system and instance status for account %s in %s', account, region)
                try:
                    status = ec2.get_all_instance_status()
                except boto.exception.EC2ResponseError, e:
                    LOG.warning('EC2 API call get_all_instance_status() failed: %s', e)
                    continue

                results = dict((i.id, s.system_status.status + ':' + s.instance_status.status)
                               for i in instances for s in status if s.id == i.id)
                for i in instances:
                    if i.id in results:
                        self.info[i.id]['status'] = results[i.id]
                    else:
                        self.info[i.id]['status'] = u'not-available:not-available'

        # Delete all alerts from EC2 if instance has expired
        url = 'http://%s:%s/alerta/api/%s/resources?tags=cloud:AWS/EC2' % (CONF.api_host, CONF.api_port, CONF.api_version)
        LOG.info('Get list of EC2 alerts from %s', url)
        try:
            response = json.loads(urllib2.urlopen(url, None, 15).read())['response']
        except urllib2.URLError, e:
            LOG.error('Could not get list of alerts from resources located in EC2: %s', e)
            response = None

        if response and 'resources' in response and 'resourceDetails' in response['resources']:
            LOG.info('Retrieved list of %s EC2 instances', response['total'])
            resource_details = response['resources']['resourceDetails']

            for r in resource_details:
                resource = r['resource']
                LOG.debug('Delete all alerts for %s', resource)

                # resource might be 'i-01234567:/tmp'
                if ':' in resource:
                    resource = resource.split(':')[0]

                if resource.startswith('ip-'):  # FIXME - transform ip-10-x-x-x to i-01234567
                    LOG.debug('Transforming resource %s -> %s', resource, self.lookup.get(resource, resource))
                    resource = self.lookup.get(resource, resource)

                # Delete alerts for instances that are no longer listed by EC2 API
                if resource not in self.info:
                    url = 'http://%s:%s/alerta/api/%s/resources/resource/%s' % \
                          (CONF.api_host, CONF.api_port, CONF.api_version, resource)
                    LOG.info('EC2 instance %s is no longer listed, DELETE all associated alerts', resource)
                    try:
                        request = urllib2.Request(url=url)
                        request.get_method = lambda: 'DELETE'
                        response = urllib2.urlopen(request).read()['response']
                    except urllib2.URLError, e:
                        LOG.error('API Request %s failed: %s', url, e)
                        continue

                    if response['status'] == 'ok':
                        LOG.info('Successfully deleted alerts for resource %s', resource)
                    else:
                        LOG.warning('Failed to delete alerts for resource %s: %s', resource, response['message'])

        for instance in self.info:
            for check, event in [('state', 'Ec2InstanceState'),
                                 ('status', 'Ec2StatusChecks')]:
                if instance not in self.last or check not in self.last[instance]:
                    self.last[instance] = dict()
                    self.last[instance][check] = 'unknown'

                if self.last[instance][check] != self.info[instance][check]:

                    # Defaults
                    resource = instance
                    group = 'AWS/EC2'
                    value = self.info[instance][check]
                    severity = severity_code.UNKNOWN
                    text = 'Instance was %s now it is %s' % (self.last[instance][check], self.info[instance][check])
                    environment = [self.info[instance]['stage']]
                    service = ['EC2']  # NOTE: Will be transformed to correct service using Ec2ServiceLookup
                    tags = self.info[instance]['tags']
                    correlate = ''

                    # instance-state = pending | running | shutting-down | terminated | stopping | stopped
                    if check == 'state':
                        if self.info[instance][check] == 'running':
                            severity = severity_code.NORMAL
                        else:
                            severity = severity_code.WARNING

                    # system-status = ok | impaired | initializing | insufficient-data | not-applicable
                    # instance status = ok | impaired | initializing | insufficient-data | not-applicable
                    elif check == 'status':
                        if self.info[instance][check] == 'ok:ok':
                            severity = severity_code.NORMAL
                            text = "System and instance status checks are ok"
                        elif self.info[instance][check].startswith('ok'):
                            severity = severity_code.WARNING
                            text = 'Instance status check is %s' % self.info[instance][check].split(':')[1]
                        elif self.info[instance][check].endswith('ok'):
                            severity = severity_code.WARNING
                            text = 'System status check is %s' % self.info[instance][check].split(':')[0]
                        else:
                            severity = severity_code.WARNING
                            text = 'System status check is %s and instance status check is %s' % tuple(
                                self.info[instance][check].split(':'))

                    timeout = None
                    threshold_info = None
                    summary = None
                    raw_data = None
                    more_info = None
                    graph_urls = None

                    awsAlert = Alert(
                        resource=resource,
                        event=event,
                        correlate=correlate,
                        group=group,
                        value=value,
                        severity=severity,
                        environment=environment,
                        service=service,
                        text=text,
                        event_type='cloudAlert',
                        tags=tags,
                        timeout=timeout,
                        threshold_info=threshold_info,
                        summary=summary,
                        raw_data=raw_data,
                        more_info=more_info,
                        graph_urls=graph_urls,
                    )

                    if self.dedup.is_send(awsAlert):
                        self.mq.send(awsAlert)

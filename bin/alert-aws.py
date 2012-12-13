#!/usr/bin/env python
########################################
#
# alert-aws.py - Amazon Web Service Alerter
# 
########################################

import os
import sys
import time
import urllib
import urllib2
try:
    import json
except ImportError:
    import simplejson as json
import yaml
import stomp
import datetime
import logging
import uuid

import boto.ec2

__program__ = 'alert-aws'
__version__ = '1.0.2'

BROKER_LIST  = [('localhost', 61613)] # list of brokers for failover
ALERT_QUEUE  = '/queue/alerts'
BASE_URL     = 'http://monitoring.guprod.gnl/alerta/api/v1'

DEFAULT_TIMEOUT = 86400
WAIT_SECONDS = 10

LOGFILE = '/var/log/alerta/alert-aws.log'
PIDFILE = '/var/run/alerta/alert-aws.pid'
DISABLE = '/opt/alerta/conf/alert-aws.disable'
AWSCONF = '/opt/alerta/conf/alert-aws.yaml'

EC2_REGIONS = [ 'eu-west-1', 'us-east-1' ]

SEVERITY_CODE = {
    # ITU RFC5674 -> Syslog RFC5424
    'CRITICAL':       1, # Alert
    'MAJOR':          2, # Crtical
    'MINOR':          3, # Error
    'WARNING':        4, # Warning
    'NORMAL':         5, # Notice
    'INFORM':         6, # Informational
    'DEBUG':          7, # Debug
}

# Globals
info = dict()
last = dict()

def ec2_status():
    global conn, awsconf

    last = info.copy()

    accounts = [a for a in awsconf if 'account' in a]
    for account in accounts:
        account_name = account['account']
        access_key = account.get('aws_access_key_id','')
        secret_key = account.get('aws_secret_access_key','')
        logging.debug('AWS Account=%s, AwsAccessKey=%s, AwsSecretKey=************************************%s', account_name, access_key, secret_key[-4:])

        for region in EC2_REGIONS:
            try:
                ec2 = boto.ec2.connect_to_region(region, aws_access_key_id=access_key, aws_secret_access_key=secret_key)
            except boto.exception.EC2ResponseError, e:
                logging.warning('EC2 API call connect_to_region(region=%s) failed: %s', region, e)
                continue

            try:
                reservations = ec2.get_all_instances()
            except boto.exception.EC2ResponseError, e:
                logging.warning('EC2 API call get_all_instances() failed: %s', e)
                continue

            instances = [i for r in reservations for i in r.instances]
            for i in instances:
                info[i.id] = dict()
                info[i.id]['account'] = account_name
                info[i.id]['state'] = i.state
                info[i.id]['stage'] = i.tags.get('Stage','n/a')
                info[i.id]['role'] = i.tags.get('Role','n/a')
                info[i.id]['tags'] = i.tags

            try:
                status = ec2.get_all_instance_status()
            except boto.exception.EC2ResponseError, e:
                logging.warning('EC2 API call get_all_instance_status() failed: %s', e)
                continue

            results = dict((i.id, s.system_status.status+':'+s.instance_status.status) for i in instances for s in status if s.id == i.id)
            for i in instances:
                if i.id in results:
                    info[i.id]['status'] = results[i.id]
                else:
                    info[i.id]['status'] = u'not-available:not-available'

    # Get list of all alerts from EC2
    url = '%s/alerts' % BASE_URL
    try:
        response = json.loads(urllib2.urlopen(url, None, 15).read())['response']
    except urllib2.URLError, e:
        logging.error('Could not get list of alerts from resources located in EC2: %s', e)
        response = None

    if response and 'alerts' in response and 'alertDetails' in response['alerts']:
        alertDetails = response['alerts']['alertDetails']

        for alert in alertDetails:
            alertid  = alert['id']
            resource = alert['resource']

            # resource might be 'i-01234567:/tmp'
            if ':' in resource:
                resource = resource.split(':')[0]

            if resource not in info:
                logging.info('%s : EC2 instance %s is no longer running, deleting associated alert', alertid, resource)
                url = '%s/alerts/alert/%s' % (BASE_URL, alertid)
                method_override = '{ "_method": "delete" }'
                req = urllib2.Request(url, method_override)
                try:
                    response = json.loads(urllib2.urlopen(req).read())['response']
                except urllib2.URLError, e:
                    logging.error('%s : API end-point error: %s', alertid, e)

                if response['status'] == 'ok':
                    logging.info('%s : Successfully deleted alert', alertid)
                else:
                    logging.warning('%s : Failed to delete alert: %s', alertid, response['message'])

    for instance in info:
        for check, event in [('state', 'Ec2InstanceState'),
                             ('status','Ec2StatusChecks')]:
            if instance not in last or check not in last[instance]:
                last[instance] = dict()
                last[instance][check] = 'unknown'

            if last[instance][check] != info[instance][check]:

                # Defaults
                resource    = instance
                group       = 'AWS/EC2'
                value       = info[instance][check]
                text        = 'Instance was %s now it is %s' % (last[instance][check], info[instance][check])
                environment = [ info[instance]['stage'] ]
                service     = [ 'Cloud' ]
                tags        = list()
                correlate   = ''

                # instance-state = pending | running | shutting-down | terminated | stopping | stopped
                if check == 'state':
                    if info[instance][check] == 'running':
                        severity = 'NORMAL'
                    else:
                        severity = 'WARNING'

                # system-status = ok | impaired | initializing | insufficient-data | not-applicable
                # instance status = ok | impaired | initializing | insufficient-data | not-applicable
                elif check == 'status':
                    if info[instance][check] == 'ok:ok':
                        severity = 'NORMAL'
                        text = "System and instance status checks are ok"
                    elif info[instance][check].startswith('ok'):
                        severity = 'WARNING'
                        text = 'Instance status check is %s' % info[instance][check].split(':')[1]
                    elif info[instance][check].endswith('ok'):
                        severity = 'WARNING'
                        text = 'System status check is %s' % info[instance][check].split(':')[0]
                    else:
                        severity = 'WARNING'
                        text = 'System status check is %s and instance status check is %s' % tuple(info[instance][check].split(':'))

                alertid = str(uuid.uuid4()) # random UUID
                createTime = datetime.datetime.utcnow()

                headers = dict()
                headers['type']           = "statusAlert"
                headers['correlation-id'] = alertid

                alert = dict()
                alert['id']               = alertid
                alert['resource']         = resource
                alert['event']            = event
                alert['group']            = group
                alert['value']            = value
                alert['severity']         = severity.upper()
                alert['severityCode']     = SEVERITY_CODE[alert['severity']]
                alert['environment']      = environment
                alert['service']          = service
                alert['text']             = text
                alert['type']             = 'statusAlert'
                alert['tags']             = tags
                alert['summary']          = '%s - %s %s is %s on %s %s' % (','.join(environment), severity.upper(), event, value, ','.join(service), resource)
                alert['createTime']       = createTime.replace(microsecond=0).isoformat() + ".%03dZ" % (createTime.microsecond//1000)
                alert['origin']           = "%s/%s" % (__program__, os.uname()[1])
                alert['thresholdInfo']    = 'n/a'
                alert['timeout']          = DEFAULT_TIMEOUT
                alert['correlatedEvents'] = correlate

                logging.info('%s : %s', alertid, json.dumps(alert))

                while not conn.is_connected():
                    logging.warning('Waiting for message broker to become available')
                    time.sleep(1.0)

                try:
                    conn.send(json.dumps(alert), headers, destination=ALERT_QUEUE)
                    broker = conn.get_host_and_port()
                    logging.info('%s : Alert sent to %s:%s', alertid, broker[0], str(broker[1]))
                except Exception, e:
                    logging.error('Failed to send alert to broker %s', e)

def send_heartbeat():
    global conn

    heartbeatid = str(uuid.uuid4()) # random UUID
    createTime = datetime.datetime.utcnow()

    headers = dict()
    headers['type']           = "heartbeat"
    headers['correlation-id'] = heartbeatid

    heartbeat = dict()
    heartbeat['id']         = heartbeatid
    heartbeat['type']       = "heartbeat"
    heartbeat['createTime'] = createTime.replace(microsecond=0).isoformat() + ".%03dZ" % (createTime.microsecond//1000)
    heartbeat['origin']     = "%s/%s" % (__program__,os.uname()[1])
    heartbeat['version']    = __version__

    try:
        conn.send(json.dumps(heartbeat), headers, destination=ALERT_QUEUE)
        broker = conn.get_host_and_port()
        logging.info('%s : Heartbeat sent to %s:%s', heartbeatid, broker[0], str(broker[1]))
    except Exception, e:
        logging.error('Failed to send heartbeat to broker %s', e)

def main():
    global conn, awsconf

    logging.basicConfig(level=logging.INFO, format="%(asctime)s alert-aws[%(process)d] %(levelname)s - %(message)s", filename=LOGFILE)
    logging.info('Starting up Alert Amazon Web Services EC2 version %s', __version__)

    # Write pid file if not already running
    if os.path.isfile(PIDFILE):
        pid = open(PIDFILE).read()
        try:
            os.kill(int(pid), 0)
            logging.error('Process with pid %s already exists, exiting', pid)
            sys.exit(1)
        except OSError:
            pass
    file(PIDFILE, 'w').write(str(os.getpid()))

    while os.path.isfile(DISABLE):
        logging.warning('Disable flag exists (%s). Sleeping...', DISABLE)
        time.sleep(120)

    # Read in configuration file
    try:
        awsconf = yaml.load(open(AWSCONF))
        logging.info('Loaded %d AWS account configurations OK', len(awsconf))
    except Exception, e:
        logging.warning('Failed to load AWS account configuration: %s. Exit.', e)
        sys.exit(1)

    # Connect to message broker
    try:
        conn = stomp.Connection(BROKER_LIST)
        conn.start()
        conn.connect(wait=True)
    except Exception, e:
        logging.error('Stomp connection error: %s', e)

    while True:
        try:
            ec2_status()
            send_heartbeat()
            time.sleep(WAIT_SECONDS)
        except (KeyboardInterrupt, SystemExit):
            conn.disconnect()
            os.unlink(PIDFILE)
            sys.exit(0)

if __name__ == '__main__':
    main()

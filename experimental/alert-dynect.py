#!/usr/bin/env python
########################################
#
# alert-dynect.py - Alert DynECT Monitor
#
########################################

import os
import sys
import time
try:
    import json
except ImportError:
    import simplejson
import threading
import yaml
import stomp
import datetime
import logging
import uuid
import re
from BaseHTTPServer import BaseHTTPRequestHandler as BHRH
from dynect.DynectDNS import DynectRest

__program__ = 'alert-dynect'
__version__ = '1.0.0'

BROKER_LIST  = [('localhost', 61613)] # list of brokers for failover
ALERT_QUEUE  = '/queue/alerts'
DEFAULT_TIMEOUT = 86400
#CONFIGFILE = '/opt/alerta/conf/alert-dynect.yaml'
#LOGFILE = '/var/log/alerta/alert-dynect.log'
#PIDFILE = '/var/run/alerta/alert-dynect.pid'
#DISABLE = '/opt/alerta/conf/alert-aws.disable'
CONFIGFILE = '/home/dnanini/alerta/conf/alert-dynect.yaml'
LOGFILE = '/home/dnanini/alerta/alert-dynect.log'
PIDFILE = '/home/dnanini/alerta/alert-dynect.pid'
DISABLE = '/home/dnanini/alerta/conf/alert-aws.disable'

REPEAT_LIMIT = 10
repeats = REPEAT_LIMIT

#_check_rate   = 600             # Check rate of alerts
_check_rate   = 15

# Global variables
config = dict()
info = dict()
last = dict()
dynect = []

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

class WorkerThread(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        global conn, repeats, last

        queryDynect()

        logging.info('Tokens: %d' % repeats)

        for item in info:

            # Defaults
            resource    = item
            group       = 'Network'
            value       = info[item]
            environment = [ 'PROD' ]
            service     = [ 'Infrastructure' ]
            tags        = ''
            correlate   = ''
            event       = ''
            text        = 'Item was %s now it is %s.' % (info[item], last[item])

            # gslb status	= ok | unk | trouble | failover
            # pool status	= up | unk | down
            # pool serve_mode	= obey | always | remove | no

            if repeats == 10:

                logging.info('Resending state of %s' % item)

                if item.startswith('gslb-'):

                    if 'ok' in info[item]:
                        event = 'GSLBOK'
                        severity = 'NORMAL'
                        text = 'GSLB state -> status: %s.' % (info[item])

                elif item.startswith('pool-'):

                    if 'up:obey:' in info[item]:
                        event = 'PoolUp'
                        severity = 'NORMAL'
                        text = 'Pool state -> status: %s serve_mode: %s weight: %s.' % tuple(info[item].split(':'))

                alertid = str(uuid.uuid4()) # random UUID
                createTime = datetime.datetime.utcnow()

                headers = dict()
                headers['type']           = "serviceAlert"
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
                alert['type']             = 'dynectAlert'
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
                    time.sleep(30.0)

                try:
                    conn.send(json.dumps(alert), headers, destination=ALERT_QUEUE)
                    broker = conn.get_host_and_port()
                    logging.info('%s : Alert sent to %s:%s', alertid, broker[0], str(broker[1]))
                except Exception, e:
                    logging.error('Failed to send alert to broker %s', e)

            logging.info('Comparing GSLB or Pool. %s' % item)

            if last[item] != info[item]:

                logging.info('GSLB or Pool state change from %s to %s' % (info[item], last[item]))

                if item.startswith('gslb-'):

                    text = 'GSLB status is %s.' % last[item]

                    if 'ok' in info[item]:
                        event = 'GSLBOK'
                        severity = 'NORMAL'
                    else:
                        event = 'GSLBNotOK'
                        severity = 'CRITICAL'

                elif item.startswith('pool-'):

                    text = 'Pool is in state -> status: %s serve_mode: %s weight: %s and should be in state -> status: %s serve_mode: %s weight: %s' % tuple(last[item].split(':') + info[item].split(':'))

                    if 'down' in info[item]: 
                        event = 'PoolDown'
                        severity = 'MAYOR'
                    elif 'obey' not in info[item]:
                        event = 'PoolServeMode'
                        severity = 'WARNING'
                    elif 'up:obey:' in info[item]:
                        event = 'PoolUp'
                        severity = 'NORMAL'
                    else:
                        event = 'PoolStateChange'
                        severity = 'WARNING'

                alertid = str(uuid.uuid4()) # random UUID
                createTime = datetime.datetime.utcnow()

                headers = dict()
                headers['type']           = "serviceAlert"
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
                alert['type']             = 'dynectAlert'
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
                    time.sleep(30.0)

                try:
                    conn.send(json.dumps(alert), headers, destination=ALERT_QUEUE)
                    broker = conn.get_host_and_port()
                    logging.info('%s : Alert sent to %s:%s', alertid, broker[0], str(broker[1]))
                except Exception, e:
                    logging.error('Failed to send alert to broker %s', e)

        last = info.copy()

        if repeats:
            repeats -= 1
        else:
            repeats = REPEAT_LIMIT

        return

class MessageHandler(object):

    def on_error(self, headers, body):
        logging.error('Received an error %s', body)

    def on_disconnected(self):
        global conn

        logging.warning('Connection lost. Attempting auto-reconnect to %s', ALERT_QUEUE)
        conn.start()
        conn.connect(wait=True)
        conn.subscribe(destination=ALERT_QUEUE, ack='auto')

# Initialise Config
def init_config():

    global config, repeats, last

    logging.info('Loading config...')

    try:
        config = yaml.load(open(CONFIGFILE))
    except Exception, e:
        logging.error('Failed to load config: %s', e)
    logging.info('Loaded %d config OK', len(config))

    REPEAT_LIMIT = config['repeats']
    repeats = REPEAT_LIMIT

    queryDynect()
    last = info.copy()

def queryDynect():

    global dynect, info

    logging.info('Quering DynECT to get the state of GSLBs')

    # Creating DynECT API session 
    try:
        rest_iface = DynectRest()
        response = rest_iface.execute('/Session/', 'POST', config)

        if response['status'] != 'success':
            logging.error('Incorrect credentials')
            sys.exit(1)

        # Discover all the Zones in DynECT
        response = rest_iface.execute('/Zone/', 'GET')
        zone_resources = response['data']

        # Discover all the LoadBalancers
        for item in zone_resources:
            zone = item.split('/')[3]
            response = rest_iface.execute('/LoadBalance/'+zone+'/','GET')
            gslb = response['data']

            # Discover LoadBalancer pool information.
            for lb in gslb:
                fqdn = lb.split('/')[4]
                dynect.append(zone+'/'+fqdn)
                response = rest_iface.execute('/LoadBalance/'+zone+'/'+fqdn+'/','GET')
                info['gslb-'+fqdn] = response['data']['status']

                for i in range(0,len(response['data']['pool'])):
                    name = '%s-%s' % (fqdn, response['data']['pool'][i]['label'])
                    state = '%s:%s:%s' % (response['data']['pool'][i]['status'], response['data']['pool'][i]['serve_mode'], response['data']['pool'][i]['weight'])
                    info['pool-'+name] = state

        logging.info('Finish quering and object discovery.')
        logging.info('GSLBs and Pools: %s', json.dumps(info))

        rest_iface.execute('/Session/', 'DELETE')

    except Exception, e:
        logging.error('Failed to discover GSLBs: %s', e)
        pass

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
    global config, conn

    logging.basicConfig(level=logging.INFO, format="%(asctime)s alert-dynect[%(process)d] %(threadName)s %(levelname)s - %(message)s", filename=LOGFILE)
    logging.info('Starting up DynECT GSLB monitor version %s', __version__)

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

    # Connect to message broker
    logging.info('Connect to broker')
    try:
        conn = stomp.Connection(
                   BROKER_LIST,
                   reconnect_sleep_increase = 5.0,
                   reconnect_sleep_max = 120.0,
                   reconnect_attempts_max = 20
               )
        conn.set_listener('', MessageHandler())
        conn.start()
        conn.connect(wait=True)
    except Exception, e:
        logging.error('Stomp connection error: %s', e)
        sys.exit(1)

    # Initialiase config
    init_config()
    config_mod_time = os.path.getmtime(CONFIGFILE)

    # Start worker threads
    w = WorkerThread()
    logging.info('Starting thread: %s', '')

    while True:
        try:
            # Read (or re-read) config as necessary
            if os.path.getmtime(CONFIGFILE) != config_mod_time:
                init_config()
                config_mod_time = os.path.getmtime(CONFIGFILE)

            w.run()
            send_heartbeat()
            time.sleep(_check_rate)

        except (KeyboardInterrupt, SystemExit):
            conn.disconnect()
            w.join()
            os.unlink(PIDFILE)
            logging.info('Graceful exit.')
            sys.exit(0)

if __name__ == '__main__':
    main()

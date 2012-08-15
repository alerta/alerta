#!/usr/bin/env python
########################################
#
# alert-ganglia.py - Alert Ganglia module
#
########################################

import os
import sys
import urllib2
try:
    import json
except ImportError:
    import simplejson as json
import yaml
import stomp
import datetime
import time
import logging
import uuid
import re

__program__ = 'alert-ganglia'
__version__ = '1.7.1'

BROKER_LIST  = [('localhost', 61613)] # list of brokers for failover
ALERT_QUEUE  = '/queue/alerts'
EXPIRATION_TIME = 600 # seconds = 10 minutes

WAIT_SECONDS = 120

# API_SERVER = 'ganglia.guprod.gnl'
API_SERVER='ganglia.gul3.gnl'

RULESFILE = '/opt/alerta/conf/alert-ganglia.yaml'
LOGFILE = '/var/log/alerta/alert-ganglia.log'
PIDFILE = '/var/run/alerta/alert-ganglia.pid'

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

def get_metrics(filter):

    url = "http://%s/ganglia/api/v1/metrics?%s" % (API_SERVER, filter)
    logging.info('Metric request %s', url)

    try:
        output = urllib2.urlopen(url).read()
        response = json.loads(output)['response']
    except urllib2.URLError, e:
        logging.error('Could not retrieve data and/or parse metric data from %s - %s', url, e)
        return dict()

    if response['status'] == 'error':
        logging.error('No metrics retreived - %s', response['message'])
        return dict()

    logging.info('Retreived %s matching metrics in %ss', response['total'], response['time'])

    return response['metrics']

def send_heartbeat():
    global conn

    heartbeatid = str(uuid.uuid4()) # random UUID
    createTime = datetime.datetime.utcnow()

    headers = dict()
    headers['type']           = "heartbeat"
    headers['correlation-id'] = heartbeatid
    # headers['persistent']     = 'false'
    # headers['expires']        = int(time.time() * 1000) + EXPIRATION_TIME * 1000

    heartbeat = dict()
    heartbeat['id']         = heartbeatid
    heartbeat['type']       = "heartbeat"
    heartbeat['createTime'] = createTime.replace(microsecond=0).isoformat() + ".%03dZ" % (createTime.microsecond//1000)
    heartbeat['origin']     = "%s/%s" % (__program__,os.uname()[1])
    heartbeat['version']    = __version__

    try:
        conn.send(json.dumps(heartbeat), headers, destination=ALERT_QUEUE)
    except Exception, e:
        logging.error('Failed to send heartbeat to broker %s', e)
    broker = conn.get_host_and_port()
    logging.info('%s : Heartbeat sent to %s:%s', heartbeatid, broker[0], str(broker[1]))

def init_rules():
    rules = list()

    logging.info('Loading rules...')
    try:
        rules = yaml.load(open(RULESFILE))
    except Exception, e:
        logging.error('Failed to load alert rules: %s', e)
        return rules

    logging.info('Loaded %d rules OK', len(rules))
    return rules

def main():
    global conn

    logging.basicConfig(level=logging.INFO, format="%(asctime)s alert-ganglia[%(process)d] %(levelname)s - %(message)s", filename=LOGFILE)
    logging.info('Starting up Alert Ganglia version %s', __version__)

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
        conn = stomp.Connection(BROKER_LIST)
        conn.start()
        conn.connect(wait=True)
    except Exception, e:
        logging.error('Stomp connection error: %s', e)

    # Initialiase alert rules
    rules = init_rules()
    rules_mod_time = os.path.getmtime(RULESFILE)

    while True:
        try:
            # Read (or re-read) rules as necessary
            if os.path.getmtime(RULESFILE) != rules_mod_time:
                rules = init_rules()
                rules_mod_time = os.path.getmtime(RULESFILE)

            for rule in rules:
                response = get_metrics(rule['filter'])
                # logging.debug('%s', response)

                env = dict()
                svc = dict()
                value = dict()
                tags = dict()
                for m in response:
                    if m['metric'] in rule['value']:
                        logging.debug('%s', m)

                        resource = re.sub('\$instance', m.get('instance','__NA__'), rule['resource'])
                        resource = re.sub('\$host', m.get('host','__NA__'), resource)
                        resource = re.sub('\$cluster', m.get('cluster','__NA__'), resource)

                        if '__NA__' in resource: continue

                        if 'environment' not in rule:
                            env[resource] = m['environment']
                        else:
                            env[resource] = rule['environment']
                        if 'service' not in rule:
                            svc[resource] = m['service']
                        else:
                            svc[resource] = m['service']

                        if 'value' in m:
                            v = m['value']
                        else:
                            v = m['sum'] # FIXME - sum or sum/num or whatever

                        value[resource] = re.sub('\$now', str(time.time()), rule['value'])
                        value[resource] = re.sub('\$%s' % m['metric'], v, value[resource])
                        value[resource] = re.sub('\$%s' % m['metric'], v, value[resource])

                        tags[resource] = 'cluster:%s' % m['cluster']

                for resource in value:
                    index = 0
                    try:
                        calculated_value = eval(value[resource])
                    except SyntaxError:
                        calculated_value = 'unknown'

                    for ti in rule['thresholdInfo']:
                        sev,op,threshold = ti.split(':')
                        threshold = re.sub('\$now', str(time.time()), threshold)
                        rule_eval = '%s %s %s' % (calculated_value,op,threshold)
                        try:
                            result = eval(rule_eval)
                        except SyntaxError:
                            result = False
                        if result:
                            logging.debug('%s %s %s %s rule fired %s %s %s %s',env[resource], svc[resource], sev,rule['event'],resource,ti, rule['text'][index], calculated_value)
                            alertid = str(uuid.uuid4()) # random UUID
                            createTime = datetime.datetime.utcnow()

                            headers = dict()
                            headers['type']           = "gangliaAlert"
                            headers['correlation-id'] = alertid
                            headers['persistent']     = 'true'
                            headers['expires']        = int(time.time() * 1000) + EXPIRATION_TIME * 1000

                            # standard alert info
                            alert = dict()
                            alert['id']               = alertid
                            alert['resource']         = resource
                            alert['event']            = rule['event']
                            alert['group']            = rule['group']
                            alert['value']            = calculated_value
                            alert['severity']         = sev
                            alert['severityCode']     = SEVERITY_CODE[sev]
                            alert['environment']      = env[resource]
                            alert['service']          = svc[resource]
                            alert['text']             = rule['text'][index]
                            alert['type']             = 'gangliaAlert'
                            alert['tags']             = list(rule['tags'])
                            alert['summary']          = '%s - %s %s is %s on %s %s' % (env[resource], sev, rule['event'], calculated_value, svc[resource], resource)
                            alert['createTime']       = createTime.replace(microsecond=0).isoformat() + ".%03dZ" % (createTime.microsecond//1000)
                            alert['origin']           = "%s/%s" % (__program__, os.uname()[1])
                            alert['thresholdInfo']    = rule['thresholdInfo']
                            alert['timeout']          = 86400  # expire alerts after 1 day
                            alert['moreInfo']         = ''
                            alert['graphs']           = ''

                            # Add machine tags
                            alert['tags'].append(tags[resource])

                            logging.info('%s : %s', alertid, json.dumps(alert))

                            try:
                                conn.send(json.dumps(alert), headers, destination=ALERT_QUEUE)
                            except Exception, e:
                                logging.error('Failed to send alert to broker %s', e)
                                sys.exit(1) # XXX - do I really want to exit here???
                            broker = conn.get_host_and_port()
                            logging.info('%s : Alert sent to %s:%s', alertid, broker[0], str(broker[1]))

                            break # First match wins
                        index += 1

            send_heartbeat()
            logging.info('Rule check is sleeping %d seconds', WAIT_SECONDS)
            time.sleep(WAIT_SECONDS)

        except (KeyboardInterrupt, SystemExit):
            conn.disconnect()
            os.unlink(PIDFILE)
            sys.exit(0)

if __name__ == '__main__':
    main()

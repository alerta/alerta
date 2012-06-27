#!/usr/bin/env python
########################################
#
# alert-ganglia.py - Alert Ganglia module
#
########################################

# TODO
# 1. query for cluster metrics so can alert off them too

import os
import sys
import optparse
import time
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
import re

__version__ = '1.5.3'

BROKER_LIST  = [('localhost', 61613)] # list of brokers for failover
ALERT_QUEUE  = '/queue/alerts'
EXPIRATION_TIME = 600 # seconds = 10 minutes

API_SERVER = 'ganglia.guprod.gnl:80'
API_VERSION = 'latest'
# METRIC_API = 'http://%s/ganglia/api/%s/metric-data' % (API_SERVER, API_VERSION)
METRIC_API = 'http://%s/ganglia/api/snapshot.py' % (API_SERVER)

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

_check_rate   = 120             # Check rate of alerts

# Global variables
environment = None

host_info = dict()
host_metrics = dict()
rules = dict()

currentCount  = dict()
currentState  = dict()
previousSeverity = dict()

# Convert string to number
def num(value):
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except:
        return value

# Query Ganglia Snapshot API for metric data
def get_metrics():
    global _refresh_rate, environment, host_info, host_metrics

    now = time.time()

    url = "%s?environment=%s" % (METRIC_API, environment)
    logging.info('Getting metrics from %s', url)

    try:
        output = urllib2.urlopen(url).read()
        response = json.loads(output)
    except urllib2.URLError, e:
        logging.error('Could not retrieve data from %s - %s', url, e)
        return

    logging.info('Snapshot taken at %s', response['response']['localTime'])

    host_info = {}
    host_metrics = {}

    hosts = [host for host in response['response']['hosts']]
    for h in hosts:
        host_info[h['host']] = dict()
        host_info[h['host']] = {
            'id':          h['id'],
            'environment': h['environment'],
            'grid':        h['grid'],
            'cluster':     h['cluster'],
            'ipAddress':   h['ipAddress'],
            'location':    h['location'],
            'uptime':      h['gmondStarted'],
            'graphUrl':    h.get('graphUrl', 'none')
        }

        host_metrics[h['host']] = dict()

    # logging.debug('%s', json.dumps(host_info))

    metrics = [metric for metric in response['response']['metrics'] if metric.has_key('value') and (metric['slope'] == u'both' or metric['slope'] == u'zero' or metric['units'] == u'timestamp')]
    for m in metrics:
        host_metrics[m['host']][m['metric']] = {
            'id':          m['id'],
            'environment': m['environment'],
            'grid':        m['grid'], 
            'cluster':     m['cluster'], 
            'host':        m['host'],
            'metric':      m['metric'],
            'value':       num(m['value']),
            'age':         m['age'],
            'type':        'TBC',
            'slope':       m['slope'],
            'units':       m['units'],
            'group':       m['group'],
            'graphUrl':    m.get('graphUrl', 'none')
        }

    # logging.debug('%s', json.dumps(host_metrics))

    diff = time.time() - now
    logging.info('Updated %d host info and %d host metrics and it took %.2f seconds', len(host_info), len(host_metrics), diff)

# Initialise Rules
def init_rules():
    global rules
    logging.info('Loading rules...')
    try:
        rules = yaml.load(open(RULESFILE))
    except Exception, e:
        logging.error('Failed to load alert rules: %s', e)
    for r in rules:
        check_rule(r['rule'])
    logging.info('Loaded %d rules OK', len(rules))

# Rule validation
def check_rule(rule):
    dummy_variable = 1
    try:
        test = re.sub(r'(\$([A-Za-z0-9-_]+))', 'dummy_variable', rule)
        eval (test)
    except SyntaxError, e:
        logging.error('SyntaxError in rule %s %s', rule, e)
        sys.exit(3)

def main():
    global environment, host_info, host_metrics, rules

    logging.basicConfig(level=logging.INFO, format="%(asctime)s alert-ganglia[%(process)d] %(levelname)s - %(message)s", filename=LOGFILE)
    logging.info('Starting up Alert Ganglia version %s', __version__)

    # Command line options
    parser = optparse.OptionParser(version='%prog '+__version__)
    parser.add_option("-E", "--environment", dest="environment", help="Environment eg. PROD, REL, QA, TEST, CODE, STAGE, DEV, LWP, INFRA")
    parser.add_option("-p", "--pid-file", dest="pidfile", help="Pidfile")

    options, args = parser.parse_args()
    environment = options.environment

    if options.pidfile:
        PIDFILE = options.pidfile

    # Write pid file
    if os.path.isfile(PIDFILE):
        logging.error('%s already exists, exiting', PIDFILE)
        sys.exit(1)
    else:
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
    init_rules()
    rules_mod_time = os.path.getmtime(RULESFILE)

    while True:
        try:
            get_metrics()

            # Read (or re-read) rules as necessary
            if os.path.getmtime(RULESFILE) != rules_mod_time:
                init_rules()
                rules_mod_time = os.path.getmtime(RULESFILE)

            for r in rules:
                for h in host_info:
                    m = re.search(r['resource'], host_info[h]['id'])
                    if not m:
                        logging.debug('%s %s: Skip rule %s %s as no match for target %s', r['event'], r['severity'], r['resource'], r['rule'], h)
                        continue

                    # Make substitutions to evaluate expression
                    evalStr = r['rule']
                    now = time.time()
                    evalStr = evalStr.replace('$now', str(now))
                    evalStr = re.sub(r'(\$([A-Za-z0-9-_]+))', r"host_metrics[h]['\2']['value']", evalStr)
                    try:
                        result = eval (evalStr)
                    except KeyError, e:
                        logging.debug('Host %s does not have metric values to evaluate rule %s', h, evalStr)
                        continue
                    except ZeroDivisionError, e:
                        logging.debug('Host %s rule eval generated a ZeroDivisionError on %s', h, evalStr)
                        continue
                        
                    if result:
                        logging.debug('%s %s %s: Rule %s %s is True', h, r['event'], r['severity'], r['resource'], r['rule'])

                        # Set necessary state variables if currentState is unknown
                        if (h, r['event']) not in currentState:
                            currentState[(h, r['event'])] = r['severity']
                            currentCount[(h, r['event'], r['severity'])] = 0
                            previousSeverity[(h, r['event'])] = r['severity']
    
                        if currentState[(h, r['event'])] != r['severity']:                                                          # Change of threshold state
                            currentCount[(h, r['event'], r['severity'])] = currentCount.get((h, r['event'], r['severity']), 0) + 1
                            currentCount[(h, r['event'], currentState[(h, r['event'])])] = 0                                        # zero-out previous sev counter
                            currentState[(h, r['event'])] = r['severity']
                        elif currentState[(h, r['event'])] == r['severity']:                                                        # Threshold state has not changed
                            currentCount[(h, r['event'], r['severity'])] += 1

                        logging.debug('currentState = %s, currentCount = %d', currentState[(h, r['event'])], currentCount[(h, r['event'], r['severity'])])

                        # Determine if should send a repeat alert 
                        repeat = (currentCount[(h, r['event'], r['severity'])] - r.get('count', 1)) % r.get('repeat', 1) == 0

                        logging.debug('Send alert if prevSev %s != %s AND thresh %d == %s', previousSeverity[(h, r['event'])], r['severity'], currentCount[(h, r['event'], r['severity'])], r.get('count', 1))
                        logging.debug('Send repeat alert = %s (%d - %d %% %d)', repeat, currentCount[(h, r['event'], r['severity'])], r.get('count', 1), r.get('repeat', 1))
   
                        # Determine if current threshold count requires an alert
                        if ((previousSeverity[(h, r['event'])] != r['severity'] and currentCount[(h, r['event'], r['severity'])] == r.get('count', 1))
                            or (previousSeverity[(h, r['event'])] == r['severity'] and repeat)):

                            # Subsitute real values into alert description where required
                            descrStr = r['description']
                            matches = re.findall(r'(\$[A-Za-z0-9-_]+)', descrStr)
                            for m in matches:
                                name = m.lstrip('$')
                                m = '\\' + m
                                try:
                                    if host_metrics[h][name]['units'] == 'timestamp':
                                        descrStr = re.sub(m, time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(host_metrics[h][name]['value'])), descrStr)
                                    else:
                                        descrStr = re.sub(m, str(host_metrics[h][name]['value']), descrStr)
                                except Exception:
                                    descrStr += '[FAILED TO PARSE]'

                            # Subsitute real values into alert description where required
                            valueStr = r['value']
                            matches = re.findall(r'(\$[A-Za-z0-9-_]+)', valueStr)
                            for m in matches:
                                name = m.lstrip('$')
                                m = '\\' + m
                                try:
                                    if host_metrics[h][name]['units'] == 'timestamp' or name == 'boottime':
                                        valueStr = re.sub(m, time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(host_metrics[h][name]['value'])), valueStr)
                                    else:
                                        valueStr = re.sub(m, str(host_metrics[h][name]['value']), valueStr)
                                except Exception:
                                    valueStr += '[FAILED TO PARSE]'

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
                            alert['resource']         = host_info[h]['id']
                            alert['event']            = r['event']
                            alert['group']            = r['group']
                            alert['value']            = valueStr
                            alert['severity']         = r['severity']
                            alert['severityCode']     = SEVERITY_CODE[r['severity']]
                            alert['environment']      = host_info[h]['environment']
                            alert['service']          = host_info[h]['grid']
                            alert['text']             = descrStr
                            alert['type']             = 'gangliaAlert'
                            alert['tags']             = r['tags'] + [ "location:"+host_info[h]['location'], "cluster:"+host_info[h]['cluster'] ]
                            alert['summary']          = '%s - %s %s is %s on %s %s' % (host_info[h]['environment'], r['severity'], r['event'], valueStr, host_info[h]['grid'], h)
                            alert['createTime']       = createTime.replace(microsecond=0).isoformat() + ".%06dZ" % createTime.microsecond
                            alert['origin']           = "alert-ganglia/%s" % os.uname()[1]
                            alert['thresholdInfo']    = "%s: %s x %s" % (r['resource'], r['rule'], r['count'])
                            if r['severity'] == 'NORMAL':
                                alert['timeout'] = 600    # expire NORMAL alerts after 10 minutes
                            else:
                                alert['timeout'] = 86400  # expire non-NORMAL alerts after 1 day
                            alert['moreInfo']         = host_info[h]['graphUrl']

                            alert['graphs']           = list()
                            for g in r['graphs']:
                                try:
                                    alert['graphs'].append(host_metrics[h][g]['graphUrl'])
                                except KeyError:
                                    continue

                            logging.info('%s : %s', alertid, json.dumps(alert))

                            try:
                                conn.send(json.dumps(alert), headers, destination=ALERT_QUEUE)
                            except Exception, e:
                                logging.error('Failed to send alert to broker %s', e)
                                sys.exit(1) # XXX - do I really want to exit here???
                            broker = conn.get_host_and_port()
                            logging.info('%s : Alert sent to %s:%s', alertid, broker[0], str(broker[1]))
    
                            # Keep track of previous severity
                            previousSeverity[(h, r['event'])] = r['severity']

                    else:
                        logging.debug('%s %s %s: Rule %s %s is False', h, r['event'], r['severity'], r['resource'], r['rule'])

            logging.info('Rule check is sleeping %d seconds', _check_rate)
            time.sleep(_check_rate)

        except (KeyboardInterrupt, SystemExit):
            conn.disconnect()
            os.unlink(PIDFILE)
            sys.exit(0)

if __name__ == '__main__':
    main()

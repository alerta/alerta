#!/usr/bin/env python
########################################
#
# alert-ganglia.py - Alert Ganglia module
#
########################################

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

__version__ = '1.6.3'

BROKER_LIST  = [('localhost', 61613)] # list of brokers for failover
ALERT_QUEUE  = '/queue/alerts'
EXPIRATION_TIME = 600 # seconds = 10 minutes

API_SERVER = 'ganglia.guprod.gnl'

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
FAIL = 1

_check_rate   = 120             # Check rate of alerts

# Global variables
host_info = dict()
host_metrics = dict()
rules = dict()

currentCount  = dict()
currentState  = dict()
previousSeverity = dict()

# XXX - Replace this with /ganglia/api/v1/grids? API query
ENVIRONMENTS = [ 'PROD', 'REL', 'QA', 'TEST', 'CODE', 'DEV', 'STAGE', 'LWP', 'INFRA' ]
SERVICES = [ 'ContentAPI', 'Discussion', 'EC2', 'FlexibleContent', 'Identity', 'MicroApp', 'Mutual', 'R1', 'R2', 'SharedSvcs', 'Soulmates', 'SLM', 'Servers', 'Network' ]

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

# Query Ganglia metric API
def get_metrics(env,svc):
    global host_info, host_metrics

    now = time.time()

    url = "http://%s/ganglia/api/v1/metrics?environment=%s&service=%s" % (API_SERVER, env, svc)
    logging.info('Getting metrics from %s', url)

    try:
        output = urllib2.urlopen(url).read()
        response = json.loads(output)['response']
    except urllib2.URLError, e:
        logging.error('Could not retrieve data and/or parse metric data from %s - %s', url, e)
        return 1

    logging.info('%s metrics retreived at %s local time', response['total'], response['localTime'])

    host_info = {}
    host_metrics = {}

    hosts = [host for host in response['hosts']]
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

    metrics = [metric for metric in response['metrics'] if metric.has_key('value')]
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
            'units':       m['units'],
            'group':       m['group'],
            'graphUrl':    m.get('graphUrl', 'none')
        }

    diff = time.time() - now
    logging.info('Updated %s %s host info for %s servers and %s host metrics in %.2f seconds', env, svc, len(host_info), len(host_metrics), diff)

    return 0

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

def eval_rule(r,h):
    global conn

    m = re.search(r['resource'], host_info[h]['id'])
    if not m:
        logging.debug('%s %s: Skip rule %s %s as no match for target %s', r['event'], r['severity'], r['resource'], r['rule'], h)
        return

    # Make substitutions to evaluate expression
    evalStr = r['rule']
    now = time.time()
    evalStr = evalStr.replace('$now', str(now))
    evalStr = re.sub(r'(\$([A-Za-z0-9-_]+))', r"host_metrics[h]['\2']['value']", evalStr)
    try:
        result = eval (evalStr)
    except KeyError, e:
        logging.debug('Host %s does not have metric values to evaluate rule %s', h, evalStr)
        return
    except ZeroDivisionError, e:
        logging.debug('Host %s rule eval generated a ZeroDivisionError on %s', h, evalStr)
        return

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
            alert['tags']             = list(r['tags'])
            alert['summary']          = '%s - %s %s is %s on %s %s' % (host_info[h]['environment'], r['severity'], r['event'], valueStr, host_info[h]['grid'], h)
            alert['createTime']       = createTime.replace(microsecond=0).isoformat() + ".%03dZ" % (createTime.microsecond//1000)
            alert['origin']           = "alert-ganglia/%s" % os.uname()[1]
            alert['thresholdInfo']    = "%s: %s x %s" % (r['resource'], r['rule'], r['count'])
            if r['severity'] == 'NORMAL':
                alert['timeout'] = 600    # expire NORMAL alerts after 10 minutes
            else:
                alert['timeout'] = 86400  # expire non-NORMAL alerts after 1 day
            alert['moreInfo']         = host_info[h]['graphUrl']

            # Add machine tags
            alert['tags'].append("location:"+host_info[h]['location'])
            alert['tags'].append("cluster:"+host_info[h]['cluster'])
            alert['tags'].append("os:"+host_metrics[h]['os_name']['value'].lower())

            alert['graphs']           = list()
            for g in r['graphs']:
                try:
                    alert['graphs'].append(host_metrics[h][g]['graphUrl'])
                except KeyError:
                    return

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

def main():
    global conn, host_info, host_metrics, rules

    logging.basicConfig(level=logging.INFO, format="%(asctime)s alert-ganglia[%(process)d] %(levelname)s - %(message)s", filename=LOGFILE)
    logging.info('Starting up Alert Ganglia version %s', __version__)

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
            # Read (or re-read) rules as necessary
            if os.path.getmtime(RULESFILE) != rules_mod_time:
                init_rules()
                rules_mod_time = os.path.getmtime(RULESFILE)

            # Get metric data for all environments and services
            for env in ENVIRONMENTS:
                for svc in SERVICES:

                    if get_metrics(env,svc) == FAIL:
                        continue

                    for rule in rules:
                        for host in host_info:
                            eval_rule(rule,host)

            logging.info('Rule check is sleeping %d seconds', _check_rate)
            time.sleep(_check_rate)

        except (KeyboardInterrupt, SystemExit):
            conn.disconnect()
            os.unlink(PIDFILE)
            sys.exit(0)

if __name__ == '__main__':
    main()


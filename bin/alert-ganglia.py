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
__version__ = '1.8.8'

BROKER_LIST  = [('localhost', 61613)] # list of brokers for failover
ALERT_QUEUE  = '/queue/alerts'
EXPIRATION_TIME = 600 # seconds = 10 minutes

WAIT_SECONDS = 120

# API_SERVER = 'ganglia.guprod.gnl:8080'
API_SERVER = 'localhost:8080'
REQUEST_TIMEOUT = 30

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

currentCount  = dict()
currentState  = dict()
previousSeverity = dict()

def get_metrics(filter):

    url = "http://%s/ganglia/api/v1/metrics?%s" % (API_SERVER, filter)
    logging.info('Metric request %s', url)

    try:
        r = urllib2.urlopen(url, None, REQUEST_TIMEOUT)
    except urllib2.URLError, e:
        logging.error('Could not retrieve metric data from %s - %s', url, e)
        return dict()

    if r.getcode() is None:
        logging.error('Error during connection or data transfer (timeout=%d)', REQUEST_TIMEOUT)
        return dict()

    response = json.loads(r.read())['response']
    if response['status'] == 'error':
        logging.error('No metrics retreived - %s', response['message'])
        return dict()

    logging.info('Retreived %s matching metrics in %ss', response['total'], response['time'])

    return response['metrics']

class MessageHandler(object):

    def on_error(self, headers, body):
        logging.error('Received an error %s', body)

    def on_disconnected(self):
        global conn

        logging.warning('Connection lost. Attempting auto-reconnect to %s', ALERT_QUEUE)
        conn.start()
        conn.connect(wait=True)
        conn.subscribe(destination=ALERT_QUEUE, ack='auto')

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

def quote(s):
    try:
        return int(s)
    except TypeError:
        float(s)
        return "%.1f" % float(s)
    except ValueError:
        return '"%s"' % s

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

    # Initialiase alert rules
    rules = init_rules()
    rules_mod_time = os.path.getmtime(RULESFILE)

    while True:
        try:
            # Read (or re-read) rules as necessary
            #if os.path.getmtime(RULESFILE) != rules_mod_time:
            #    rules = init_rules()
            #    rules_mod_time = os.path.getmtime(RULESFILE)

            rules = init_rules() # re-read rule config each time

            for rule in rules:
                # Check rule is valid
                if len(rule['thresholdInfo']) != len(rule['text']):
                    logging.error('Invalid rule for %s - must be an alert text for each threshold.', rule['event'])
                    continue

                # Get list of metrics required to evaluate each rule
                params = dict()
                if 'filter' in rule and rule['filter'] is not None:
                    params[rule['filter']] = 1

                for s in (' '.join(rule['text']), ' '.join(rule['thresholdInfo']), rule['value']):
                    matches = re.findall('\$([a-z0-9A-Z_]+)', s)
                    for m in matches:
                        if m != 'now':
                            params['metric='+m] = 1
                filter = '&'.join(params)

                # Get metric data for each rule
                response = get_metrics(filter)

                # Make non-metric substitutions
                now = time.time()
                rule['value'] = re.sub('\$now', str(now), rule['value'])
                idx = 0
                for threshold in rule['thresholdInfo']:
                    rule['thresholdInfo'][idx] = re.sub('\$now', str(now), threshold)
                    idx += 1
                idx = 0
                for text in rule['text']:
                    rule['text'][idx] = re.sub('\$now', time.strftime('%Y/%m/%d %H:%M:%S', time.localtime(now)), text)
                    idx += 1

                metric = dict()
                for m in response:

                    resource = re.sub('\$instance', m.get('instance','__NA__'), rule['resource'])
                    resource = re.sub('\$host', m.get('host','__NA__'), resource)
                    resource = re.sub('\$cluster', m.get('cluster','__NA__'), resource)
                    if '__NA__' in resource: continue

                    # Dont generate cluster alerts from host-based metrics
                    if 'host' in m and not '$host' in rule['resource']:
                        continue

                    if resource not in metric:
                        metric[resource] = dict()
                    if 'thresholdInfo' not in metric[resource]:
                        metric[resource]['thresholdInfo'] = list(rule['thresholdInfo'])
                    if 'text' not in metric[resource]:
                        metric[resource]['text'] = list(rule['text'])

                    if m['metric'] in rule['value']:

                        if 'environment' not in rule:
                            metric[resource]['environment'] = [m['environment']]
                        else:
                            metric[resource]['environment'] = [rule['environment']]
                        if 'service' not in rule:
                            metric[resource]['service'] = [m['service']]
                        else:
                            metric[resource]['service'] = [rule['service']]

                        if 'value' in m:
                            v = quote(m['value'])
                        elif rule['value'].endswith('.sum'):
                            v = quote(m['sum'])
                        else:
                            try:
                                v = "%.1f" % (float(m['sum']) / float(m['num']))
                            except ZeroDivisionError:
                                v = 0.0

                        if 'value' not in metric[resource]:
                            metric[resource]['value'] = rule['value']
                        metric[resource]['value'] = re.sub('\$%s(\.sum)?' % m['metric'], str(v), metric[resource]['value'])
                        metric[resource]['units'] = m['units']

                        metric[resource]['tags'] = list()
                        metric[resource]['tags'].extend(rule['tags'])
                        metric[resource]['tags'].append('cluster:%s' % m['cluster'])
                        if 'tags' in m and m['tags'] is not None:
                            metric[resource]['tags'].extend(m['tags'])

                        if 'graphUrl' not in metric[resource]:
                            metric[resource]['graphUrl'] = list()
                        if 'graphUrl' in m:
                            metric[resource]['graphUrl'].append(m['graphUrl'])

                        for g in rule['graphs']:
                            if '$host' in rule['resource'] and 'graphUrl' in m:
                                metric[resource]['graphUrl'].append('/'.join(m['graphUrl'].rsplit('/',2)[0:2])+'/graph.php?c=%s&h=%s&m=%s&r=1day&v=0&z=default' % (m['cluster'], m['host'], g))
                            if '$cluster' in rule['resource'] and 'graphUrl' in m:
                                metric[resource]['graphUrl'].append('/'.join(m['graphUrl'].rsplit('/',2)[0:2])+'/graph.php?c=%s&m=%s&r=1day&v=0&z=default' % (m['cluster'], g))

                        metric[resource]['moreInfo'] = ''
                        if '$host' in rule['resource'] and 'graphUrl' in m:
                            metric[resource]['moreInfo'] = '/'.join(m['graphUrl'].rsplit('/',2)[0:2])+'/?c=%s&h=%s' % (m['cluster'], m['host'])
                        if '$cluster' in rule['resource'] and 'graphUrl' in m:
                            metric[resource]['moreInfo'] = '/'.join(m['graphUrl'].rsplit('/',2)[0:2])+'/?c=%s' % m['cluster']

                    if m['metric'] in ''.join(rule['thresholdInfo']):

                        if 'value' in m:
                            v = quote(m['value'])
                        elif rule['value'].endswith('.sum'):
                            v = quote(m['sum'])
                        else:
                            try:
                                v = "%.1f" % (float(m['sum']) / float(m['num']))
                            except ZeroDivisionError:
                                v = 0.0

                        idx = 0
                        for threshold in metric[resource]['thresholdInfo']:
                            metric[resource]['thresholdInfo'][idx] = re.sub('\$%s(\.sum)?' % m['metric'], str(v), threshold)
                            idx += 1

                    if m['metric'] in ''.join(rule['text']):

                        if 'value' in m:
                            v = quote(m['value'])
                        elif rule['value'].endswith('.sum'):
                            v = quote(m['sum'])
                        else:
                            try:
                                v = "%.1f" % (float(m['sum']) / float(m['num']))
                            except ZeroDivisionError:
                                v = 0.0

                        if m['type'] == 'timestamp' or m['units'] == 'timestamp':
                            v = time.strftime('%Y/%m/%d %H:%M:%S', time.localtime(float(v)))

                        idx = 0
                        for text in metric[resource]['text']:
                            metric[resource]['text'][idx] = re.sub('\$%s(\.sum)?' % m['metric'], str(v), text)
                            idx += 1

                for resource in metric:
                    index = 0
                    try:
                        calculated_value = eval(metric[resource]['value'])
                    except KeyError:
                        logging.warning('Could not calculate %s value for %s because %s is not being reported', rule['event'], resource, rule['value'])
                        continue
                    except (SyntaxError,NameError):
                        logging.error('Could not calculate %s value for %s => eval(%s)', rule['event'], resource, metric[resource]['value'])
                        continue

                    for ti in metric[resource]['thresholdInfo']:
                        sev,op,threshold = ti.split(':')
                        rule_eval = '%s %s %s' % (quote(calculated_value),op,threshold)
                        try:
                            result = eval(rule_eval)
                        except SyntaxError:
                            logging.error('Could not evaluate %s threshold for %s => eval(%s)', rule['event'], resource, rule_eval)
                            result = False

                        if result:

                            # Set necessary state variables if currentState is unknown
                            if (resource, rule['event']) not in currentState:
                                currentState[(resource, rule['event'])] = sev
                                currentCount[(resource, rule['event'], sev)] = 0
                                previousSeverity[(resource, rule['event'])] = sev

                            if currentState[(resource, rule['event'])] != sev:                                                          # Change of threshold state
                                currentCount[(resource, rule['event'], sev)] = currentCount.get((resource, rule['event'], sev), 0) + 1
                                currentCount[(resource, rule['event'], currentState[(resource, rule['event'])])] = 0                                        # zero-out previous sev counter
                                currentState[(resource, rule['event'])] = sev
                            elif currentState[(resource, rule['event'])] == sev:                                                        # Threshold state has not changed
                                currentCount[(resource, rule['event'], sev)] += 1

                            logging.debug('currentState = %s, currentCount = %d', currentState[(resource, rule['event'])], currentCount[(resource, rule['event'], sev)])

                            # Determine if should send a repeat alert
                            try:
                                repeat = (currentCount[(resource, rule['event'], sev)] - rule.get('count', 1)) % rule.get('repeat', 1) == 0
                            except:
                                repeat = False

                            logging.debug('Send alert if prevSev %s != %s AND thresh %d == %s', previousSeverity[(resource, rule['event'])], sev, currentCount[(resource, rule['event'], sev)], rule.get('count', 1))
                            logging.debug('Repeat? %s (%d - %d %% %d)', repeat, currentCount[(resource, rule['event'], sev)], rule.get('count', 1), rule.get('repeat', 1))

                            # Determine if current threshold count requires an alert
                            if ((previousSeverity[(resource, rule['event'])] != sev and currentCount[(resource, rule['event'], sev)] == rule.get('count', 1))
                                or (previousSeverity[(resource, rule['event'])] == sev and repeat)):

                                logging.debug('%s %s %s %s rule fired %s %s %s %s', ','.join(metric[resource]['environment']), ','.join(metric[resource]['service']), sev,rule['event'],resource,ti, rule['text'][index], calculated_value)

                                alertid = str(uuid.uuid4()) # random UUID
                                createTime = datetime.datetime.utcnow()

                                headers = dict()
                                headers['type']           = "gangliaAlert"
                                headers['correlation-id'] = alertid

                                # standard alert info
                                alert = dict()
                                alert['id']               = alertid
                                alert['resource']         = resource
                                alert['event']            = rule['event']
                                alert['group']            = rule['group']
                                alert['value']            = str(calculated_value)+' '+metric[resource]['units']
                                alert['severity']         = sev
                                alert['severityCode']     = SEVERITY_CODE[sev]
                                alert['environment']      = metric[resource]['environment']
                                alert['service']          = metric[resource]['service']
                                alert['text']             = metric[resource]['text'][index]
                                alert['type']             = 'gangliaAlert'
                                alert['tags']             = metric[resource]['tags']
                                alert['summary']          = '%s - %s %s is %s on %s %s' % (','.join(metric[resource]['environment']), sev, rule['event'], alert['value'], ','.join(metric[resource]['service']), resource)
                                alert['createTime']       = createTime.replace(microsecond=0).isoformat() + ".%03dZ" % (createTime.microsecond//1000)
                                alert['origin']           = "%s/%s" % (__program__, os.uname()[1])
                                alert['thresholdInfo']    = ','.join(rule['thresholdInfo'])
                                alert['timeout']          = 86400  # expire alerts after 1 day
                                alert['moreInfo']         = metric[resource]['moreInfo']
                                alert['graphs']           = metric[resource]['graphUrl']

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

                                # Keep track of previous severity
                                previousSeverity[(resource, rule['event'])] = sev

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

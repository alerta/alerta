#!/usr/bin/env python
########################################
#
# alert-ganglia.py - Alerter Ganglia module
#
########################################

# Sends Ganglia alerts to a message bus

# TODO
# 1. query for cluster metrics so can alert off them too

import os
import sys
import optparse
import time
import threading
import urllib2
try:
    import json
except ImportError:
    import simplejson as json
import stomp
import datetime
import logging
import copy
import uuid
import re

__version__ = "1.4"

BROKER_LIST  = [('devmonsvr01',61613), ('localhost', 61613)] # list of brokers for failover
ALERT_QUEUE  = '/queue/alerts'

API_SERVER = 'ganglia.gul3.gnl:80'
API_VERSION = 'latest'
# METRIC_API = 'http://%s/ganglia/api/%s/metric-data' % (API_SERVER, API_VERSION)
METRIC_API = 'http://%s/ganglia/api/snapshot.py' % (API_SERVER)

RULESFILE = '/opt/alerta/conf/alert-ganglia.rules'
LOGFILE = '/var/log/alerta/alert-ganglia.log'
PIDFILE = '/var/run/alerta/alert-ganglia.pid'

_WorkerThread = None            # Worker thread object
_Lock = threading.Lock()        # Synchronization lock
_refresh_rate = 120             # Refresh rate of the data
_check_rate   = 60              # Check rate of alerts

currentCount  = dict()
currentState  = dict()
previousAlert = dict()

updates = 0

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
class UpdateMetricThread(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self.running      = False
        self.shuttingdown = False

        self._hosts        = {}
        self._metrics      = {}
        self.timeout       = 2

    def shutdown(self):
        self.shuttingdown = True
        if not self.running:
            return
        self.join()

    def run(self):
        global _refresh_rate, environment, host_info, host_metrics, updates
        self.running = True

        while not self.shuttingdown:
            if self.shuttingdown:
                break

            now = time.time()

            url = "%s?environment=%s" % (METRIC_API, environment)
            logging.info('Getting metrics from %s', url)

            try:
                output = urllib2.urlopen(url).readlines()
                response = json.loads(''.join(output))
            except urllib2.URLError, e:
                logging.error('Could not retrieve data from %s - %s', url, e)
                return

            hosts = [host for host in response['response']['hosts']]
            for h in hosts:
                self._hosts[h['host']] = dict()
                self._hosts[h['host']]['id']           = h['id']
                self._hosts[h['host']]['environment']  = str(h['environment'])
                self._hosts[h['host']]['grid']         = str(h['grid'])
                self._hosts[h['host']]['cluster']      = str(h['cluster'])
                self._hosts[h['host']]['ipAddress']    = str(h['ipAddress'])
                self._hosts[h['host']]['location']     = str(h['location'])
                self._hosts[h['host']]['gmondStarted'] = str(h['gmondStarted'])
                self._hosts[h['host']]['type']         = 'TBC'
                self._hosts[h['host']]['graphUrl']     = h.get('graphUrl', 'none')

                self._metrics[h['host']] = dict()

            # logging.info('%s', json.dumps(self._hosts))

            metrics = [metric for metric in response['response']['metrics'] if metric.has_key('value') and (metric['slope'] == u'both' or metric['slope'] == u'zero' or metric['units'] == u'timestamp')]
            for m in metrics:
                self._metrics[m['host']][m['metric']] = {
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
                    'graphUrl':    m.get('graphUrl', 'none') }

                if m['host'] == 'devmonsvr01' and m['metric'] == 'swap_util':
                    logging.debug('%s', json.dumps(self._metrics[m['host']][m['metric']]))

            # logging.info('%s', json.dumps(self._metrics))

            _Lock.acquire()
            host_info    = copy.deepcopy(self._hosts)
            host_metrics = copy.deepcopy(self._metrics)
            _Lock.release()

            diff = time.time() - now
            logging.info('Updated %d host info and %d host metrics and it took %.2f seconds', len(host_info), len(host_metrics), diff)
            updates += 1

            if not self.shuttingdown:
                logging.debug('Metric gather is sleeping %d seconds', _refresh_rate)
                time.sleep(_refresh_rate)

        self.running = False

# Initialise Rules
def init_rules():
    global rules
    logging.info('Re-initialising rules')
    try:
        rules = json.loads(''.join(open(RULESFILE)))
    except Exception, e:
        logging.error('Could not re-load alerta rules: %s', e)
    for r in rules:
        check_rule(r['rule'])
    logging.info('Rules loaded OK')

# Rule validation
def check_rule(rule):

    # logging.info('Checking rule %s', rule) 
    dummy_variable = 1
    try:
        test = re.sub(r'(\$([A-Za-z0-9-_]+))', 'dummy_variable', rule)
        eval (test)
    except SyntaxError, e:
        logging.error('ERROR: SyntaxError in rule %s %s', rule, e)
        os._exit(1)

def main():
    global environment, host_info, host_metrics

    host_info = dict()
    host_metrics = dict()
    rules = dict()

    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s alert-ganglia[%(process)d] %(levelname)s - %(message)s", filename=LOGFILE)
    logging.info('Starting up Alert Ganglia version %s', __version__)

    # Command line options
    parser = optparse.OptionParser(version='%prog '+__version__)
    parser.add_option("-E", "--environment", dest="environment", help="Environment eg. PROD, REL, QA, TEST, CODE, STAGE, DEV, LWP, INFRA")
    parser.add_option("-p", "--pid-file", dest="pidfile", help="Pidfile")

    (options, args) = parser.parse_args()
    environment = options.environment

    if options.pidfile:
        PIDFILE = options.pidfile

    # Write pid file
    if os.path.isfile(PIDFILE):
        logging.error('%s already exists, exiting' % PIDFILE)
        sys.exit(1)
    else:
        file(PIDFILE, 'w').write(str(os.getpid()))

    # Connect to message broker
    try:
        conn = stomp.Connection(BROKER_LIST)
        # conn.set_listener('', MessageHandler())
        conn.start()
        conn.connect(wait=True)
        # conn.subscribe(destination=NOTIFY_TOPIC, ack='auto', headers={'selector': "repeat = 'false'"}) # TODO - subscribe to a 'heartbeat' channel for PING/PONGs
    except Exception, e:
        logging.error('Stomp connection error: %s', e)

    # Start metric update thread
    logging.info('Start update metric thread')
    _WorkerThread = UpdateMetricThread()
    _WorkerThread.start()

    # Initialiase Rules
    logging.info('Initialising rules')
    try:
        rules = json.loads(''.join(open(RULESFILE)))
    except Exception, e:
        logging.error('Could not load alerta rules: %s', e)
        sys.exit(1)
    for r in rules:
        check_rule(r['rule'])
    logging.info('Rules loaded OK')

    rules_mod_time = os.path.getmtime(RULESFILE)

    while True:
        try:
            # Read (or re-read) rules as necessary
            if os.path.getmtime(RULESFILE) != rules_mod_time:
                init_rules()
                rules_mod_time = os.path.getmtime(RULESFILE)

            for r in rules:
                for h in host_info:
                    m = re.search(r['target'], host_info[h]['id'])
                    if not m:
                        logging.debug('%s Rule %s target %s does not match host %s', r['severity'], r['rule'], r['target'], h)
                        continue

                    # Make substitutions to evaluate expression
                    evalStr = r['rule']
                    now = time.time()
                    evalStr = evalStr.replace('$now', str(now))
                    evalStr = re.sub(r'(\$([A-Za-z0-9-_]+))', r"host_metrics[h]['\2']['value']", evalStr)
                    try:
                        result = eval (evalStr)
                    except KeyError, e:
                        # logging.warning('WARNING: host %s does not have metric values to evaluate rule %s', h, evalStr)
                        continue
                        
                    # logging.debug('host %s has metric values to evaluate rule %s => %s', h, evalStr, result)

                    if result:
                        logging.debug('%s Rule EVAL is TRUE: %s against rule %s', r['severity'], h, evalStr)

                        logging.debug('Updates = %s', updates)
                        # Set necessary state variables if currentState is unknown
                        if (h, r['event']) not in currentState:
                            currentState[(h, r['event'])] = r['severity']

                            currentCount[(h, r['event'], r['severity'])] = 0
                            if updates > 1:
                                previousAlert[(h, r['event'])] = '(unknown)'
                            else:
                                previousAlert[(h, r['event'])] = r['severity']

                            logging.debug('Update # is %s -> prevSev set to %s', updates, previousAlert[(h, r['event'])])
                            logging.debug('New alert set currentCount to 0')
    
                        # Change of threshold state
                        if currentState[(h, r['event'])] != r['severity']:
                            currentCount[(h, r['event'], r['severity'])] = currentCount.get((h, r['event'], r['severity']), 0) + 1
                            currentCount[(h, r['event'], currentState[(h, r['event'])])] = 0 # zero-out previous sev counter
                            currentState[(h, r['event'])] = r['severity']
    
                        # Threshold state has not changed
                        elif currentState[(h, r['event'])] == r['severity']:
                            currentCount[(h, r['event'], r['severity'])] += 1
                            logging.debug('Inc currentCount by one if state hasnt changed, now %s', currentCount[(h, r['event'], r['severity'])])

                        if currentCount[(h, r['event'], r['severity'])] > r.get('count', 1):
                            repeat = (currentCount[(h, r['event'], r['severity'])] - r.get('count', 1)) % r.get('repeat', 1) == 0
                        else:
                            repeat = False

                        logging.debug('IF prevSev %s != %s AND thresh %d == %s', previousAlert[(h, r['event'])], r['severity'], currentCount[(h, r['event'], r['severity'])], r.get('count', 1))
                        logging.debug('IF prevSev %s == %s AND repeat? %s', previousAlert[(h, r['event'])], r['severity'], repeat)
    
                        # Determine if current threshold count requires an alert
                        if ((previousAlert[(h, r['event'])] != r['severity'] and currentCount[(h, r['event'], r['severity'])] == r.get('count', 1))
                            or (previousAlert[(h, r['event'])] == r['severity'] and repeat)):

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
                                except:
                                    descrStr += '[FAILED TO PARSE]'

                            # Subsitute real values into alert description where required
                            valueStr = r['value']
                            matches = re.findall(r'(\$[A-Za-z0-9-_]+)', valueStr)
                            for m in matches:
                                name = m.lstrip('$')
                                m = '\\' + m
                                try:
                                    if host_metrics[h][name]['units'] == 'timestamp':
                                        valueStr = re.sub(m, time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(host_metrics[h][name]['value'])), valueStr)
                                    else:
                                        valueStr = re.sub(m, str(host_metrics[h][name]['value']), valueStr)
                                except:
                                    valueStr += '[FAILED TO PARSE]'

                            alertid = str(uuid.uuid4()) # random UUID

                            headers = dict()
                            headers['type'] = "text"
                            headers['correlation-id'] = alertid

                            # standard alert info
                            alert = dict()
                            alert['id']               = alertid
                            alert['source']           = host_info[h]['id']
                            alert['event']            = r['event']
                            alert['group']            = r['group']
                            alert['value']            = valueStr
                            alert['severity']         = r['severity']
                            if repeat == False:
                                alert['previousSeverity'] = previousAlert[(h, r['event'])]
                            alert['environment']      = host_info[h]['environment']
                            alert['service']          = host_info[h]['grid']
                            alert['text']             = descrStr
                            alert['type']             = 'gangliaAlert'
                            alert['tags']             = r['tags'] + [ "location:"+host_info[h]['location'], "cluster:"+host_info[h]['cluster'] ]
                            alert['summary']          = '%s - %s %s is %s on %s %s' % (host_info[h]['environment'], r['severity'], r['event'], valueStr, host_info[h]['grid'], h)
                            alert['createTime']       = datetime.datetime.utcnow().isoformat()+'+00:00'
                            alert['moreInfo']         = host_info[h]['graphUrl']
                            alert['origin']           = "alert-ganglia/%s" % os.uname()[1]
                            alert['alertRule']        = "%s: %s x %s" % (r['target'], r['rule'], r['count'])
                            alert['repeat']           = repeat

                            alert['graphs']           = list()
                            for g in r['graphs']:
                                alert['graphs'].append(host_metrics[h][g]['graphUrl'])


                            logging.info('%s %s %s %s -> %s', alertid, h, r['event'], previousAlert[(h, r['event'])], r['severity'])

                            try:
                                conn.send(json.dumps(alert), headers, destination=ALERT_QUEUE)
                            except Exception, e:
                                logging.error('Failed to send alert to broker %s', e)
                                sys.exit(1) # XXX - do I really want to exit here???
                            broker = conn.get_host_and_port()
                            logging.info('%s : Alert sent to %s:%s', alertid, broker[0], str(broker[1]))
    
                            # Keep track of previous alert
                            previousAlert[(h, r['event'])] = r['severity']

            time.sleep(_check_rate)

        except KeyboardInterrupt, SystemExit:
            conn.disconnect()
            _WorkerThread.shutdown()
            os.unlink(PIDFILE)
            sys.exit()

if __name__ == '__main__':
    main()

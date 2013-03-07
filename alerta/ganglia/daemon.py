
import os
import sys
import urllib2
import json
import datetime
import time
import uuid
import re

import yaml
import stomp

from alerta.common import config
from alerta.common import log as logging
from alerta.common.daemon import Daemon
from alerta.alert import Alert, Heartbeat
from alerta.alert import syslog
from alerta.common.mq import Messaging

Version = '2.0.0'

LOG = logging.getLogger(__name__)
CONF = config.CONF

RULESFILE = '/opt/alerta/alerta/alert-ganglia.yaml'

currentCount = dict()
currentState = dict()
previousSeverity = dict()


class GangliaDaemon(Daemon):

    def run(self):
        
        self.running = True

        # Connect to message queue
        self.mq = Messaging()
        self.mq.connect()

        # Initialiase alert rules
        rules = GangliaDaemon.init_rules()
        rules_mod_time = os.path.getmtime(RULESFILE)

        while not self.shuttingdown:
            try:
                # Read (or re-read) rules as necessary
                #if os.path.getmtime(RULESFILE) != rules_mod_time:
                #    rules = init_rules()
                #    rules_mod_time = os.path.getmtime(RULESFILE)

                rules = GangliaDaemon.init_rules()  # re-read rule config each time

                self.check(rules)

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

    def check(self, rules):

        for rule in rules:
            # Check rule is valid
            if len(rule['thresholdInfo']) != len(rule['text']):
                LOG.error('Invalid rule for %s - must be an alert text for each threshold.', rule['event'])
                continue

            # Get list of metrics required to evaluate each rule
            params = dict()
            if 'filter' in rule and rule['filter'] is not None:
                params[rule['filter']] = 1

            for s in (' '.join(rule['text']), ' '.join(rule['thresholdInfo']), rule['value']):
                matches = re.findall('\$([a-z0-9A-Z_]+)', s)
                for m in matches:
                    if m != 'now':
                        params['metric=' + m] = 1
            filter = '&'.join(params)

            # Get metric data for each rule
            response = GangliaDaemon.get_metrics(filter)

            # Make non-metric substitutions
            now = int(time.time())
            rule['value'] = re.sub('\$now', str(now), rule['value'])
            idx = 0
            for threshold in rule['thresholdInfo']:
                rule['thresholdInfo'][idx] = re.sub('\$now', str(now), threshold)
                idx += 1
            idx = 0
            for text in rule['text']:
                rule['text'][idx] = re.sub('\$now', time.strftime('%Y/%m/%d %H:%M:%S', time.localtime(now)),
                                           text)
                idx += 1

            metric = dict()
            for m in response:

                resource = re.sub('\$instance', m.get('instance', '__NA__'), rule['resource'])
                resource = re.sub('\$host', m.get('host', '__NA__'), resource)
                resource = re.sub('\$cluster', m.get('cluster', '__NA__'), resource)
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
                        v = GangliaDaemon.quote(m['value'])
                    elif rule['value'].endswith('.sum'):
                        v = GangliaDaemon.quote(m['sum'])
                    else:
                        try:
                            v = "%.1f" % (float(m['sum']) / float(m['num']))
                        except ZeroDivisionError:
                            v = 0.0

                    if 'value' not in metric[resource]:
                        metric[resource]['value'] = rule['value']
                    metric[resource]['value'] = re.sub('\$%s(\.sum)?' % m['metric'], str(v),
                                                       metric[resource]['value'])
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
                            metric[resource]['graphUrl'].append('/'.join(m['graphUrl'].rsplit('/', 2)[
                                                                         0:2]) + '/graph.php?c=%s&h=%s&m=%s&r=1day&v=0&z=default' % (
                                                                    m['cluster'], m['host'], g))
                        if '$cluster' in rule['resource'] and 'graphUrl' in m:
                            metric[resource]['graphUrl'].append('/'.join(m['graphUrl'].rsplit('/', 2)[
                                                                         0:2]) + '/graph.php?c=%s&m=%s&r=1day&v=0&z=default' % (
                                                                    m['cluster'], g))

                    metric[resource]['moreInfo'] = ''
                    if '$host' in rule['resource'] and 'graphUrl' in m:
                        metric[resource]['moreInfo'] = '/'.join(
                            m['graphUrl'].rsplit('/', 2)[0:2]) + '/?c=%s&h=%s' % (m['cluster'], m['host'])
                    if '$cluster' in rule['resource'] and 'graphUrl' in m:
                        metric[resource]['moreInfo'] = '/'.join(m['graphUrl'].rsplit('/', 2)[0:2]) + '/?c=%s' % m['cluster']

            if m['metric'] in ''.join(rule['thresholdInfo']):

                if 'value' in m:
                    v = GangliaDaemon.quote(m['value'])
                elif rule['value'].endswith('.sum'):
                    v = GangliaDaemon.quote(m['sum'])
                else:
                    try:
                        v = "%.1f" % (float(m['sum']) / float(m['num']))
                    except ZeroDivisionError:
                        v = 0.0

                idx = 0
                for threshold in metric[resource]['thresholdInfo']:
                    metric[resource]['thresholdInfo'][idx] = re.sub('\$%s(\.sum)?' % m['metric'], str(v),
                                                                    threshold)
                    idx += 1

            if m['metric'] in ''.join(rule['text']):

                if 'value' in m:
                    v = GangliaDaemon.quote(m['value'])
                elif rule['value'].endswith('.sum'):
                    v = GangliaDaemon.quote(m['sum'])
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
                LOG.warning('Could not calculate %s value for %s because %s is not being reported',
                            rule['event'], resource, rule['value'])
                continue
            except (SyntaxError, NameError):
                LOG.error('Could not calculate %s value for %s => eval(%s)', rule['event'], resource,
                          metric[resource]['value'])
                continue
            except ZeroDivisionError:
                LOG.debug(
                    'Could not calculate %s value for %s => eval(%s) (division by zero).  Setting to 0 instead.',
                    rule['event'], resource, metric[resource]['value'])
                calculated_value = 0
                continue
            except:
                LOG.error('Could not calculate %s value for %s => eval(%s) (threw unknown exception)',
                          rule['event'], resource, metric[resource]['value'])
                continue

            LOG.debug('For resource %s got calculated_value %s ', resource, calculated_value)

            for ti in metric[resource]['thresholdInfo']:
                sev, op, threshold = ti.split(':')
                rule_eval = '%s %s %s' % (GangliaDaemon.quote(calculated_value), op, threshold)
                try:
                    result = eval(rule_eval)
                except SyntaxError:
                    LOG.error('Could not evaluate %s threshold for %s => eval(%s)', rule['event'],
                              resource, rule_eval)
                    result = False

                if result:

                    # Set necessary state variables if currentState is unknown
                    if (resource, rule['event']) not in currentState:
                        currentState[(resource, rule['event'])] = sev
                        currentCount[(resource, rule['event'], sev)] = 0
                        previousSeverity[(resource, rule['event'])] = sev

                    if currentState[(resource, rule[
                        'event'])] != sev:                                                          # Change of threshold state
                        currentCount[(resource, rule['event'], sev)] = currentCount.get(
                            (resource, rule['event'], sev), 0) + 1
                        currentCount[(resource, rule['event'], currentState[(resource, rule[
                            'event'])])] = 0                                        # zero-out previous sev counter
                        currentState[(resource, rule['event'])] = sev
                    elif currentState[(resource, rule[
                        'event'])] == sev:                                                        # Threshold state has not changed
                        currentCount[(resource, rule['event'], sev)] += 1

                    LOG.debug('calculated_value = %s, currentState = %s, currentCount = %d',
                              calculated_value, currentState[(resource, rule['event'])],
                              currentCount[(resource, rule['event'], sev)])

                    # Determine if should send a repeat alert
                    try:
                        repeat = (currentCount[(resource, rule['event'], sev)] - rule.get('count',
                                                                                          1)) % rule.get(
                            'repeat', 1) == 0
                    except:
                        repeat = False

                    LOG.debug('Send alert if prevSev %s != %s AND thresh %d == %s',
                              previousSeverity[(resource, rule['event'])], sev,
                              currentCount[(resource, rule['event'], sev)], rule.get('count', 1))
                    LOG.debug('Repeat? %s (%d - %d %% %d)', repeat,
                              currentCount[(resource, rule['event'], sev)], rule.get('count', 1),
                              rule.get('repeat', 1))

                    # Determine if current threshold count requires an alert
                    if ((previousSeverity[(resource, rule['event'])] != sev and currentCount[
                        (resource, rule['event'], sev)] == rule.get('count', 1))
                        or (previousSeverity[(resource, rule['event'])] == sev and repeat)):

                        LOG.debug('%s %s %s %s rule fired %s %s %s %s',
                                  ','.join(metric[resource]['environment']),
                                  ','.join(metric[resource]['service']), sev, rule['event'], resource,
                                  ti, rule['text'][index], calculated_value)

                        event = rule['event']
                        group = rule['group']
                        value = "%s%s" % (calculated_value, GangliaDaemon.format_units(metric[resource]['units']))
                        severity = sev
                        environment = metric[resource]['environment']
                        service = metric[resource]['service']
                        text = metric[resource]['text'][index]
                        tags = metric[resource]['tags']
                        threshold_info = ','.join(rule['thresholdInfo'])
                        more_info = metric[resource]['moreInfo']
                        graphs = metric[resource]['graphUrl']

                        gangliaAlert = Alert(
                            resource=resource,
                            event=event,
                            group=group,
                            value=value,
                            severity=severity,
                            environment=environment,
                            service=service,
                            text=text,
                            event_type='gangliaAlert',
                            tags=tags,
                            threshold_info=threshold_info,
                            # more_info= more_info,  # TODO(nsatterl): add support for more info
                            # graphs= graphs,  # TODO(nsatterl): add support for graphs
                            raw_data='',  # TODO(nsatterl): put raw metric values used to do calculation here
                        )
                        self.mq.send(gangliaAlert)

                        # Keep track of previous severity
                        previousSeverity[(resource, rule['event'])] = sev

                        break  # First match wins
                index += 1

    @staticmethod
    def get_metrics(filter):
        url = "http://%s:%s/ganglia/app/v1/metrics?%s" % (CONF.ganglia_host, CONF.ganglia_port,  filter)
        LOG.info('Metric request %s', url)

        try:
            r = urllib2.urlopen(url, None, 15)
        except urllib2.URLError, e:
            LOG.error('Could not retrieve metric data from %s - %s', url, e)
            return dict()

        if r.getcode() is None:
            LOG.error('Error during connection or data transfer (timeout=%d)', 15)
            return dict()

        response = json.loads(r.read())['response']
        if response['status'] == 'error':
            LOG.error('No metrics retreived - %s', response['message'])
            return dict()

        LOG.info('Retreived %s matching metrics in %ss', response['total'], response['time'])

        return response['metrics']

    @staticmethod
    def init_rules():
        rules = list()

        LOG.info('Loading rules...')
        try:
            rules = yaml.load(open(RULESFILE))
        except Exception, e:
            LOG.error('Failed to load alert rules: %s', e)
            return rules

        LOG.info('Loaded %d rules OK', len(rules))
        return rules

    @staticmethod
    def quote(s):
        try:
            return int(s)
        except TypeError:
            float(s)
            return "%.1f" % float(s)
        except ValueError:
            return '"%s"' % s

    @staticmethod
    def format_units(units):
        if units in ['seconds', 's']:
            return 's'
        if units in ['percent', '%']:
            return '%'
        return ' ' + units

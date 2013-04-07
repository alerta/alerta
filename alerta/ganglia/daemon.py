
import time
import urllib2
import json
import re

import yaml

from alerta.common import config
from alerta.common import log as logging
from alerta.common.daemon import Daemon
from alerta.alert import Alert, Heartbeat, severity_code
from alerta.common.mq import Messaging, MessageHandler
from alerta.common.dedup import DeDup

Version = '2.0.2'

LOG = logging.getLogger(__name__)
CONF = config.CONF


class GangliaMessage(MessageHandler):

    def __init__(self, mq):
        self.mq = mq
        MessageHandler.__init__(self)

    def on_disconnected(self):
        self.mq.reconnect()


def init_rules():

    rules = list()
    LOG.info('Loading rules...')
    try:
        rules = yaml.load(open(CONF.yaml_config))
    except Exception, e:
        LOG.error('Failed to load alert rules: %s', e)
    LOG.info('Loaded %d rules OK', len(rules))

    return rules


class GangliaDaemon(Daemon):

    def __init__(self, prog):

        Daemon.__init__(self, prog)

        self.dedup = DeDup(by_value=True)

    def run(self):
        
        self.running = True

        # Connect to message queue
        self.mq = Messaging()
        self.mq.connect(callback=GangliaMessage(self.mq))

        while not self.shuttingdown:
            try:
                rules = init_rules()  # re-read rule config each time
                self.metric_check(rules)

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

    def metric_check(self, rules):

        for rule in rules:
            # Check rule is valid
            if len(rule['thresholdInfo']) != len(rule['text']):
                LOG.warning('Skipping invalid rule %s - MUST define alert text for each threshold.', rule['event'])
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
            metric_filter = '&'.join(params.keys())
            LOG.debug('Metric filter = %s', metric_filter)

            # Get metric data for each rule
            response = GangliaDaemon.get_metrics(metric_filter)
            LOG.debug('Ganglia API response: %s', response)

            # Make non-metric substitutions in value, thresholdInfo and text
            now = int(time.time())
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

                # Make metric-based substitutions in resource eg. per instance, host or cluster
                resource = re.sub('\$instance', m.get('instance', '__NA__'), rule['resource'])
                resource = re.sub('\$host', m.get('host', '__NA__'), resource)
                resource = re.sub('\$cluster', m.get('cluster', '__NA__'), resource)

                if '__NA__' in resource:
                    LOG.debug('Metric %s doesnt match resource rule %s', m['id'], rule['resource'])
                    continue

                LOG.debug('Metric %s matches rule %s => %s', m['id'], rule['resource'], resource)

                # Don't generate cluster alerts from host-based metrics
                if 'host' in m and not '$host' in rule['resource']:
                    LOG.debug('Skipping host-based metric for cluster-based rule')
                    continue

                # Build up info for alert if metric value triggers threshold
                if resource not in metric:
                    metric[resource] = dict()
                if 'thresholdInfo' not in metric[resource]:
                    metric[resource]['thresholdInfo'] = list(rule['thresholdInfo'])
                    LOG.debug('Set thresholdInfo to %s', metric[resource]['thresholdInfo'])
                if 'text' not in metric[resource]:
                    metric[resource]['text'] = list(rule['text'])
                    LOG.debug('Set text to %s', metric[resource]['text'])

                if m['metric'] in rule['value']:
                    # Determine service and environment from rule if given
                    if 'environment' in rule:
                        metric[resource]['environment'] = [rule['environment']]
                    else:
                        metric[resource]['environment'] = [m['environment']]
                    LOG.debug('Set environment for alert to %s', metric[resource]['environment'])
                    if 'service' in rule:
                        metric[resource]['service'] = [rule['service']]
                    else:
                        metric[resource]['service'] = [m['service']]
                    LOG.debug('Set service for alert to %s', metric[resource]['service'])

                    # Use raw metric value, or sum or average if aggregated metric
                    if 'value' in m:
                        v = GangliaDaemon.quote(m['value'])  # raw value
                    elif rule['value'].endswith('.sum'):
                        v = GangliaDaemon.quote(m['sum'])  # aggregated sum value if "<metric>.sum"
                    else:
                        try:
                            v = "%.1f" % (float(m['sum']) / float(m['num']))  # average of aggregate value
                        except ZeroDivisionError:
                            v = 0.0
                    LOG.debug('Value for %s on %s is %s', m['id'], resource, v)

                    # If no value assign rule value
                    # FIXME(nsatterl): what does this do?
                    if 'value' not in metric[resource]:
                        metric[resource]['value'] = rule['value']
                    metric[resource]['value'] = re.sub('\$%s(\.sum)?' % m['metric'], str(v),
                                                       metric[resource]['value'])
                    metric[resource]['units'] = m['units']

                    # Assign tags
                    metric[resource]['tags'] = list()
                    metric[resource]['tags'].extend(rule['tags'])
                    metric[resource]['tags'].append('cluster:%s' % m['cluster'])
                    if 'tags' in m and m['tags'] is not None:
                        metric[resource]['tags'].extend(m['tags'])

                    # Assign graph URL
                    if 'graphUrl' not in metric[resource]:
                        metric[resource]['graphUrls'] = list()
                    if 'graphUrl' in m:
                        metric[resource]['graphUrls'].append(m['graphUrl'])

                    for g in rule['graphs']:
                        if '$host' in rule['resource'] and 'graphUrl' in m:
                            metric[resource]['graphUrls'].append('/'.join(m['graphUrl'].rsplit('/', 2)[0:2])
                                                                + '/graph.php?c=%s&h=%s&m=%s&r=1day&v=0&z=default'
                                                                % (m['cluster'], m['host'], g))
                        if '$cluster' in rule['resource'] and 'graphUrl' in m:
                            metric[resource]['graphUrls'].append('/'.join(m['graphUrl'].rsplit('/', 2)[0:2])
                                                                + '/graph.php?c=%s&m=%s&r=1day&v=0&z=default'
                                                                % (m['cluster'], g))

                    metric[resource]['moreInfo'] = ''
                    if '$host' in rule['resource'] and 'graphUrl' in m:
                        metric[resource]['moreInfo'] = '/'.join(
                            m['graphUrl'].rsplit('/', 2)[0:2]) + '/?c=%s&h=%s' % (m['cluster'], m['host'])
                    if '$cluster' in rule['resource'] and 'graphUrl' in m:
                        metric[resource]['moreInfo'] = '/'.join(m['graphUrl'].rsplit('/', 2)[0:2]) + '/?c=%s' % m['cluster']

                # Substitutions for threshold info
                if m['metric'] in ''.join(rule['thresholdInfo']):
                    LOG.debug('Text to be substituted: %s', ''.join(rule['thresholdInfo']))
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

                # Substitutions for text
                if m['metric'] in ''.join(rule['text']):
                    LOG.debug('Text to be substituted: %s', ''.join(rule['text']))
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

                    LOG.debug('Metric resource text %s', metric)
                    idx = 0
                    for text in metric[resource]['text']:
                        metric[resource]['text'][idx] = re.sub('\$%s(\.sum)?' % m['metric'], str(v), text)
                        idx += 1
                LOG.debug('end of metric loop')

            for resource in metric:
                LOG.debug('Calculate final value for resource %s', resource)
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
                except Exception:
                    LOG.error('Could not calculate %s value for %s => eval(%s) (threw unknown exception)',
                              rule['event'], resource, metric[resource]['value'])
                    continue

                LOG.debug('Calculated value for resource %s => %s', resource, calculated_value)

                # Compare final value with each threshold
                for ti in metric[resource]['thresholdInfo']:
                    severity, op, threshold = ti.split(':')
                    rule_eval = '%s %s %s' % (GangliaDaemon.quote(calculated_value), op, threshold)
                    try:
                        result = eval(rule_eval)
                    except SyntaxError:
                        LOG.error('Could not evaluate %s threshold for %s => eval(%s)', rule['event'],
                                  resource, rule_eval)
                        result = False

                    if result:

                        event = rule['event']
                        group = rule['group']
                        value = "%s%s" % (calculated_value, GangliaDaemon.format_units(metric[resource]['units']))
                        environment = metric[resource]['environment']
                        service = metric[resource]['service']
                        text = metric[resource]['text'][index]
                        tags = metric[resource]['tags']
                        threshold_info = ','.join(rule['thresholdInfo'])
                        more_info = metric[resource]['moreInfo']
                        graph_urls = metric[resource]['graphUrls']

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
                            more_info=more_info,
                            graph_urls=graph_urls,
                            raw_data='',  # TODO(nsatterl): put raw metric values used to do calculation here
                        )

                        if self.dedup.is_send(gangliaAlert):
                            self.mq.send(gangliaAlert)

                        break  # First match wins
                    index += 1

    @staticmethod
    def get_metrics(filter):
        url = "http://%s:%s/ganglia/api/v1/metrics?%s" % (CONF.ganglia_host, CONF.ganglia_port,  filter)
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

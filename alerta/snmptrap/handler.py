
import os
import sys
import datetime
import re

from alerta.common import config
from alerta.common import log as logging
from alerta.common.alert import Alert
from alerta.common.heartbeat import Heartbeat
from alerta.common import severity_code
from alerta.common.transform import Transformers
from alerta.common.api import ApiClient
from alerta.common.graphite import StatsD


__version__ = '3.0.4'

LOG = logging.getLogger(__name__)
CONF = config.CONF


class SnmpTrapHandler(object):

    def __init__(self, prog, disable_flag=None):

        self.prog = prog
        self.disable_flag = disable_flag or CONF.disable_flag

    def start(self):

        LOG.info('Starting %s...' % self.prog)
        self.skip_on_disable()
        self.run()

    def skip_on_disable(self):

        if os.path.isfile(self.disable_flag):
            LOG.warning('Disable flag %s exists. Skipping...', self.disable_flag)
            sys.exit(0)

    def run(self):

        self.statsd = StatsD()  # graphite metrics

        data = sys.stdin.read()
        LOG.info('snmptrapd -> %r', data)
        data = unicode(data, 'utf-8', errors='ignore')
        LOG.debug('unicoded -> %s', data)

        snmptrapAlert = SnmpTrapHandler.parse_snmptrap(data)

        self.api = ApiClient()

        if snmptrapAlert:
            try:
                self.api.send(snmptrapAlert)
            except Exception, e:
                LOG.warning('Failed to send alert: %s', e)
            self.statsd.metric_send('alert.snmptrap.alerts.total', 1)

        LOG.debug('Send heartbeat...')
        heartbeat = Heartbeat(tags=[__version__])
        try:
            self.api.send(heartbeat)
        except Exception, e:
            LOG.warning('Failed to send heartbeat: %s', e)

    @staticmethod
    def parse_snmptrap(data):

        pdu_data = data.splitlines()
        varbind_list = pdu_data[:]

        trapvars = dict()
        for line in pdu_data:
            if line.startswith('$'):
                special, value = line.split(None, 1)
                trapvars[special] = value
                varbind_list.pop(0)

        if '$s' in trapvars:
            if trapvars['$s'] == '0':
                version = 'SNMPv1'
            elif trapvars['$s'] == '1':
                version = 'SNMPv2c'
            elif trapvars['$s'] == '2':
                version = 'SNMPv2u'  # not supported
            else:
                version = 'SNMPv3'
            trapvars['$s'] = version
        else:
            version = 'SNMP'

        # Get varbinds
        varbinds = dict()
        idx = 0
        for varbind in '\n'.join(varbind_list).split('~%~'):
            if varbind == '':
                break
            idx += 1
            try:
                oid, value = varbind.split(None, 1)
            except ValueError:
                oid = varbind
                value = ''
            varbinds[oid] = value
            trapvars['$' + str(idx)] = value  # $n
            LOG.debug('$%s %s', str(idx), value)

        trapvars['$q'] = trapvars['$q'].lstrip('.')  # if numeric, remove leading '.'
        trapvars['$#'] = str(idx)

        LOG.debug('varbinds = %s', varbinds)

        LOG.debug('version = %s', version)

        correlate = list()

        if version == 'SNMPv1':
            if trapvars['$w'] == '0':
                trapvars['$O'] = 'coldStart'
                correlate = ['coldStart', 'warmStart']
            elif trapvars['$w'] == '1':
                trapvars['$O'] = 'warmStart'
                correlate = ['coldStart', 'warmStart']
            elif trapvars['$w'] == '2':
                trapvars['$O'] = 'linkDown'
                correlate = ['linkUp', 'linkDown']
            elif trapvars['$w'] == '3':
                trapvars['$O'] = 'linkUp'
                correlate = ['linkUp', 'linkDown']
            elif trapvars['$w'] == '4':
                trapvars['$O'] = 'authenticationFailure'
            elif trapvars['$w'] == '5':
                trapvars['$O'] = 'egpNeighborLoss'
            elif trapvars['$w'] == '6':  # enterpriseSpecific(6)
                if trapvars['$q'].isdigit():  # XXX - specific trap number was not decoded
                    trapvars['$O'] = '%s.0.%s' % (trapvars['$N'], trapvars['$q'])
                else:
                    trapvars['$O'] = trapvars['$q']

        elif version == 'SNMPv2c':
            if 'coldStart' in trapvars['$2']:
                trapvars['$w'] = '0'
                trapvars['$W'] = 'Cold Start'
            elif 'warmStart' in trapvars['$2']:
                trapvars['$w'] = '1'
                trapvars['$W'] = 'Warm Start'
            elif 'linkDown' in trapvars['$2']:
                trapvars['$w'] = '2'
                trapvars['$W'] = 'Link Down'
            elif 'linkUp' in trapvars['$2']:
                trapvars['$w'] = '3'
                trapvars['$W'] = 'Link Up'
            elif 'authenticationFailure' in trapvars['$2']:
                trapvars['$w'] = '4'
                trapvars['$W'] = 'Authentication Failure'
            elif 'egpNeighborLoss' in trapvars['$2']:
                trapvars['$w'] = '5'
                trapvars['$W'] = 'EGP Neighbor Loss'
            else:
                trapvars['$w'] = '6'
                trapvars['$W'] = 'Enterprise Specific'
            trapvars['$O'] = trapvars['$2']  # SNMPv2-MIB::snmpTrapOID.0

        LOG.debug('trapvars = %s', trapvars)

        LOG.info('%s-Trap-PDU %s from %s at %s %s', version, trapvars['$O'], trapvars['$B'], trapvars['$x'], trapvars['$X'])

        if trapvars['$B'] != '<UNKNOWN>':
            resource = trapvars['$B']
        elif trapvars['$A'] != '0.0.0.0':
            resource = trapvars['$A']
        else:
            m = re.match(r'UDP: \[(\d+\.\d+\.\d+\.\d+)\]', trapvars['$b'])
            if m:
                resource = m.group(1)
            else:
                resource = '<NONE>'

        # Defaults
        event = trapvars['$O']
        severity = severity_code.NORMAL
        group = 'SNMP'
        value = trapvars['$w']
        text = trapvars['$W']
        environment = 'PROD'
        service = ['Network']
        attributes = {'source': trapvars['$B']}
        tags = [version]
        timeout = None
        create_time = datetime.datetime.strptime('%sT%s.000Z' % (trapvars['$x'], trapvars['$X']), '%Y-%m-%dT%H:%M:%S.%fZ')

        snmptrapAlert = Alert(
            resource=resource,
            event=event,
            correlate=correlate,
            group=group,
            value=value,
            severity=severity,
            environment=environment,
            service=service,
            text=text,
            event_type='snmptrapAlert',
            attributes=attributes,
            tags=tags,
            timeout=timeout,
            create_time=create_time,
            raw_data=data,
        )

        suppress = Transformers.normalise_alert(snmptrapAlert, trapoid=trapvars['$O'], trapvars=trapvars, varbinds=varbinds)
        if suppress:
            LOG.info('Suppressing %s SNMP trap', snmptrapAlert.event)
            LOG.debug('%s', snmptrapAlert)
            return

        SnmpTrapHandler.translate_alert(snmptrapAlert, trapvars)

        if snmptrapAlert.get_type() == 'Heartbeat':
            snmptrapAlert = Heartbeat(origin=snmptrapAlert.origin, tags=[__version__], timeout=snmptrapAlert.timeout)

        return snmptrapAlert

    @staticmethod
    def translate_alert(alert, mappings):
        """
        Take list of mappings and apply them to alert. Used by SNMP trap handler to
        translate trap variable binding like $B to actual values if they are referred
        to in any alert attribute.
        """
        LOG.debug('Translate alert using mappings: %s', mappings)

        for k, v in mappings.iteritems():
            LOG.debug('translate %s -> %s', k, v)
            alert.resource = alert.resource.replace(k, v)
            alert.event = alert.event.replace(k, v)
            alert.environment = alert.environment.replace(k, v)
            alert.severity = alert.severity.replace(k, v)
            if alert.correlate is not None:
                alert.correlate[:] = [c.replace(k, v) for c in alert.correlate]
            alert.service[:] = [s.replace(k, v) for s in alert.service]
            alert.group = alert.group.replace(k, v)
            alert.value = alert.value.replace(k, v)
            alert.text = alert.text.replace(k, v)
            if alert.tags is not None:
                alert.tags[:] = [tag.replace(k, v) for tag in alert.tags]
            if alert.attributes is not None:
                alert.attributes = dict([(attrib[0], attrib[1].replace(k, v)) for attrib in alert.attributes.iteritems()])

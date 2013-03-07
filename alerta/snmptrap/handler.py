import sys
import re

import yaml

from alerta.common import config
from alerta.common import log as logging
from alerta.alert import Alert, Heartbeat
from alerta.common.mq import Messaging

Version = '2.0.0'

LOG = logging.getLogger(__name__)
CONF = config.CONF


class SnmpTrapHandler(object):

    def run(self):

        data = sys.stdin.read()
        LOG.info('snmptrapd -> %s', data)

        snmptrapAlert = SnmpTrapHandler.parse_snmptrap(data)

        self.mq = Messaging()
        self.mq.connect()
        self.mq.send(snmptrapAlert)

        LOG.debug('Send heartbeat...')
        heartbeat = Heartbeat(version=Version)
        self.mq.send(heartbeat)

        self.mq.disconnect()

    @staticmethod
    def parse_snmptrap(data):

        split = data.splitlines()

        trapvars = dict()
        trapvars['$$'] = '$'

        agent = split.pop(0)
        transport = split.pop(0)

        # Get varbinds
        varbinds = dict()
        for idx, line in enumerate(split, start=1):
            oid, value = line.split(None, 1)
            if value.startswith('"'):
                value = value[1:-1]
            varbinds[oid] = value
            trapvars['$' + str(idx)] = value  # $n

        trapoid = trapvars['$O'] = trapvars['$2']
        try:
            enterprise, trapnumber = trapoid.rsplit('.', 1)
        except:
            enterprise, trapnumber = trapoid.rsplit('::', 1)
        enterprise = enterprise.strip('.0')

        # Get sysUpTime
        if 'DISMAN-EVENT-MIB::sysUpTimeInstance' in varbinds:
            trapvars['$T'] = varbinds['DISMAN-EVENT-MIB::sysUpTimeInstance']
        else:
            trapvars['$T'] = trapvars['$1']  # assume 1st varbind is sysUpTime

        # Get agent address and IP
        trapvars['$A'] = agent
        m = re.match('UDP: \[(\d+\.\d+\.\d+\.\d+)]', transport)
        if m:
            trapvars['$a'] = m.group(1)
        if 'SNMP-COMMUNITY-MIB::snmpTrapAddress.0' in varbinds:
            trapvars['$R'] = varbinds['SNMP-COMMUNITY-MIB::snmpTrapAddress.0']  # snmpTrapAddress

        # Get enterprise, specific and generic trap numbers
        if trapvars['$2'].startswith('SNMPv2-MIB') or trapvars['$2'].startswith('IF-MIB'):  # snmp generic traps
            if 'SNMPv2-MIB::snmpTrapEnterprise.0' in varbinds:  # snmpTrapEnterprise.0
                trapvars['$E'] = varbinds['SNMPv2-MIB::snmpTrapEnterprise.0']
            else:
                trapvars['$E'] = '1.3.6.1.6.3.1.1.5'
            trapvars['$G'] = str(int(trapnumber) - 1)
            trapvars['$S'] = '0'
        else:
            trapvars['$E'] = enterprise
            trapvars['$G'] = '6'
            trapvars['$S'] = trapnumber

        # Get community string
        if 'SNMP-COMMUNITY-MIB::snmpTrapCommunity.0' in varbinds: # snmpTrapCommunity
            trapvars['$C'] = varbinds['SNMP-COMMUNITY-MIB::snmpTrapCommunity.0']
        else:
            trapvars['$C'] = '<UNKNOWN>'

        LOG.info('agent=%s, ip=%s, uptime=%s, enterprise=%s, generic=%s, specific=%s', trapvars['$A'],
                 trapvars['$a'], trapvars['$T'], trapvars['$E'], trapvars['$G'], trapvars['$S'])
        LOG.debug('trapvars = %s', trapvars)

        # Defaults
        event = trapoid
        resource = agent.split('.')[0]
        severity = 'NORMAL'
        group = 'SNMP'
        value = trapnumber
        text = trapvars['$3']  # ie. whatever is in varbind 3
        environment = ['INFRA']
        service = ['Network']
        tags = list()
        correlate = list()
        timeout = None
        threshold_info = None
        summary = None
        suppress = False

        # Match trap to specific config and load any parsers
        # Note: any of these variables could have been modified by a parser

        try:
            trapconf = yaml.load(open(CONF.yaml_config))
        except Exception, e:
            LOG.error('Failed to load SNMP Trap configuration: %s', e)
            sys.exit(1)
        LOG.info('Loaded %d SNMP Trap configurations OK', len(trapconf))

        for t in trapconf:
            LOG.debug('trapconf: %s', t)
            if re.match(t['trapoid'], trapoid):
                if 'parser' in t:
                    LOG.debug('Loading parser %s', t['parser'])
                    try:
                        exec (open('%s/%s.py' % (CONF.parser_dir, t['parser'])))
                        LOG.info('Parser %s/%s exec OK', CONF.parser_dir, t['parser'])
                    except Exception, e:
                        LOG.warning('Parser %s failed: %s', t['parser'], e)
                if 'event' in t:
                    event = t['event']
                if 'resource' in t:
                    resource = t['resource']
                if 'severity' in t:
                    severity = t['severity']
                if 'group' in t:
                    group = t['group']
                if 'value' in t:
                    value = t['value']
                if 'text' in t:
                    text = t['text']
                if 'environment' in t:
                    environment = [t['environment']]
                if 'service' in t:
                    service = [t['service']]
                if 'tags' in t:
                    tags = t['tags']
                if 'correlate' in t:
                    correlate = t['correlate']
                if 'threshold_info' in t:
                    threshold_info = t['threshold_info']
                if 'summary' in t:
                    summary = t['summary']
                if 'timeout' in t:
                    timeout = t['timeout']
                if 'suppress' in t:
                    suppress = t['suppress']
                break

        if suppress:
            LOG.warning('Suppressing %s SNMP trap from %s', trapoid, resource)
            return

        # Trap varbind substitutions
        LOG.debug('trapvars: %s', trapvars)
        for k, v in trapvars.iteritems():
            LOG.debug('replace: %s -> %s', k, v)
            event = event.replace(k, v)
            resource = resource.replace(k, v)
            severity = severity.replace(k, v)
            group = group.replace(k, v)
            value = value.replace(k, v)
            text = text.replace(k, v)
            environment[:] = [s.replace(k, v) for s in environment]
            service[:] = [s.replace(k, v) for s in service]
            tags[:] = [s.replace(k, v) for s in tags]
            threshold_info = threshold_info.replace(k, v)

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
            tags=tags,
            timeout=timeout,
            threshold_info=threshold_info,
            summary=summary,
            raw_data=data,
        )
        LOG.debug('snmptrapAlert = %s', snmptrapAlert)

        return snmptrapAlert

import sys
import re

import yaml

from alerta.common import config
from alerta.common import log as logging
from alerta.alert import Alert, Heartbeat
from alerta.alert.severity import *
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
        severity = NORMAL
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

        suppress = snmptrapAlert.transform_alert(trapoid=trapoid)
        if suppress:
            LOG.warning('Suppressing alert %s', snmptrapAlert.get_id())
            return

        snmptrapAlert.translate(trapvars)

        return snmptrapAlert

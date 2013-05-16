
import os
import sys
import re

from alerta.common import config
from alerta.common import log as logging
from alerta.common.alert import Alert
from alerta.common.heartbeat import Heartbeat
from alerta.common import severity_code
from alerta.common.api import ApiClient

Version = '2.0.5'

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

        data = sys.stdin.read()
        LOG.info('snmptrapd -> %s', data)

        snmptrapAlert = SnmpTrapHandler.parse_snmptrap(data)

        self.api = ApiClient()

        if snmptrapAlert:
            self.api.send(snmptrapAlert)

        LOG.debug('Send heartbeat...')
        heartbeat = Heartbeat(version=Version)
        self.api.send(heartbeat)

    @staticmethod
    def parse_snmptrap(data):

        lines = data.splitlines()

        trapvars = dict()
        for line in lines:
            if line.startswith('$'):
                special, value = line.split(None, 1)
                trapvars[special] = value

        # Get varbinds
        varbinds = dict()
        idx = 1
        for varbind in lines[-1].split('~%~'):
                oid, value = varbind.split(None, 1)
                varbinds[oid] = value
                trapvars['$' + str(idx)] = value  # $n
                LOG.debug('$%s %s', str(idx), value)
                idx += 1

        LOG.debug('varbinds = %s', varbinds)

        trapoid = trapvars['$O'] = trapvars['$2']
        try:
            enterprise, trapnumber = trapoid.rsplit('.', 1)
        except ValueError:
            enterprise, trapnumber = trapoid.rsplit('::', 1)
        enterprise = enterprise.strip('.0')

        # Get sysUpTime
        if 'DISMAN-EVENT-MIB::sysUpTimeInstance' in varbinds:
            trapvars['$T'] = varbinds['DISMAN-EVENT-MIB::sysUpTimeInstance']
        else:
            trapvars['$T'] = trapvars['$1']  # assume 1st varbind is sysUpTime

        # Get agent address and IP
        if 'SNMP-COMMUNITY-MIB::snmpTrapAddress.0' in varbinds:
            trapvars['$R'] = varbinds['SNMP-COMMUNITY-MIB::snmpTrapAddress.0']  # snmpTrapAddress

        # Get enterprise, specific and generic trap numbers
        if trapvars['$2'].startswith('SNMPv2-MIB') or trapvars['$2'].startswith('IF-MIB'):  # snmp generic traps
            if 'SNMPv2-MIB::snmpTrapEnterprise.0' in varbinds:  # snmpTrapEnterprise.0
                trapvars['$E'] = varbinds['SNMPv2-MIB::snmpTrapEnterprise.0']
            else:
                trapvars['$E'] = '1.3.6.1.6.3.1.1.5'
            if trapnumber.isdigit():
                trapvars['$G'] = str(int(trapnumber) - 1)
            else:
                trapvars['$G'] = trapnumber
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

        LOG.info('PDU source=%s, %s, uptime=%s, enterprise=%s, generic=%s, specific=%s', trapvars['$B'],
                 trapvars['$b'], trapvars['$T'], trapvars['$E'], trapvars['$G'], trapvars['$S'])
        LOG.debug('trapvars = %s', trapvars)

        # Defaults
        event = trapoid
        resource = trapvars['$B']
        severity = severity_code.NORMAL
        group = 'SNMP'
        value = trapnumber
        text = trapvars['$W']  # TRAP-TYPE DESCRIPTION
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

        suppress = snmptrapAlert.transform_alert(trapoid=trapoid, trapvars=trapvars)
        if suppress:
            LOG.warning('Suppressing alert %s', snmptrapAlert.get_id())
            return

        snmptrapAlert.translate(trapvars)

        return snmptrapAlert

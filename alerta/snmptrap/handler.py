
import os
import sys
import datetime

from alerta.common import config
from alerta.common import log as logging
from alerta.common.alert import Alert
from alerta.common.heartbeat import Heartbeat
from alerta.common import severity_code
from alerta.common.api import ApiClient

Version = '2.0.7'

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

        # Get varbinds
        varbinds = dict()
        idx = 0
        for varbind in '\n'.join(varbind_list).split('~%~'):
            if varbind == '':
                break
            idx += 1
            oid, value = varbind.split(None, 1)
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

        # Defaults
        event = trapvars['$O']
        resource = trapvars['$B'] if trapvars['$B'] != '<UNKNOWN>' else trapvars['$A']
        severity = severity_code.NORMAL
        group = 'SNMP'
        value = trapvars['$w']
        text = trapvars['$W']
        environment = ['INFRA']
        service = ['Network']
        tags = [version]
        timeout = None
        threshold_info = None
        summary = None
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
            tags=tags,
            timeout=timeout,
            threshold_info=threshold_info,
            summary=summary,
            create_time=create_time,
            raw_data=data,
        )

        suppress = snmptrapAlert.transform_alert(trapoid=trapvars['$O'], trapvars=trapvars, varbinds=varbinds)
        if suppress:
            LOG.warning('Suppressing alert %s', snmptrapAlert.get_id())
            return

        snmptrapAlert.translate(trapvars)

        return snmptrapAlert


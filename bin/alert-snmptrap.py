#!/usr/bin/env python

########################################
#
# alert-snmptrap.py - Alert SNMP Trap Script
#
########################################

import os
import sys
try:
    import json
except ImportError:
    import simplejson as json
import yaml
import stomp
import time
import datetime
import logging
import uuid
import re

__version__ = '1.1.0'

BROKER_LIST  = [('localhost', 61613)] # list of brokers for failover
ALERT_QUEUE  = '/queue/alerts'
EXPIRATION_TIME = 600 # seconds = 10 minutes

LOGFILE = '/var/log/alerta/alert-snmptrap.log'
TRAPCONF = '/opt/alerta/conf/alert-snmptrap.yaml'

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

def main():

    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s alert-snmptrap[%(process)d] %(levelname)s - %(message)s", filename=LOGFILE)

    trapvars = dict()
    trapvars['$$'] = '$'
    # FIXME trapvars['$*'] = list()

    recv = sys.stdin.read().splitlines()
    logging.info('snmptrapd -> %s', json.dumps(recv))

    agent     = recv.pop(0)
    transport = recv.pop(0)

    # Get varbinds
    varbinds = dict()
    for idx, line in enumerate(recv, start=1):
        oid,value = line.split(None, 1)
        if value.startswith('"'):
            value = value[1:-1]
        varbinds[oid] = value
        trapvars['$'+str(idx)] = value # $n
        # FIXME trapvars['$*'].append(value)
    # FIXME trapvars['$#'] = idx

    trapoid = trapvars['$O'] = trapvars['$2']
    enterprise,trapnumber = trapoid.rsplit('.',1)
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
        trapvars['$R'] = varbinds['SNMP-COMMUNITY-MIB::snmpTrapAddress.0'] # snmpTrapAddress

    # Get enterprise, specific and generic trap numbers
    if trapvars['$2'].startswith('SNMPv2-MIB') or trapvars['$2'].startswith('IF-MIB'): # snmp generic traps
        if 'SNMPv2-MIB::snmpTrapEnterprise.0' in varbinds: # snmpTrapEnterprise.0
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

    logging.info('agent=%s, ip=%s, uptime=%s, enterprise=%s, generic=%s, specific=%s', trapvars['$A'], trapvars['$a'], trapvars['$T'], trapvars['$E'], trapvars['$G'], trapvars['$S'])
    logging.debug('trapvars = %s', trapvars)

    # Defaults
    event       = trapoid
    resource    = agent.split('.')[0]
    severity    = 'NORMAL'
    group       = 'SNMP'
    value       = trapnumber
    text        = trapvars['$3'] # ie. whatever is in varbind #3
    environment = 'INFRA'
    service     = 'Network'
    correlate   = list()

    # Match trap to specific config and load any parsers
    # Note: any of these variables could have been modified by a parser

    trapconf = dict()
    try:
        trapconf = yaml.load(open(TRAPCONF))
    except Exception, e:
        logging.error('Failed to load SNMP Trap configuration: %s', e)
    logging.info('Loaded %d SNMP Trap configurations OK', len(trapconf))

    for t in trapconf:
        if re.match(t['trapoid'], trapoid):
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
                environment = t['environment']
            if 'service' in t:
                service = t['service']
            if 'correlatedEvents' in t:
                correlate = t['correlatedEvents']

    # Trap variable substitution
    for v in trapvars:
        print "sub %s %s" % ('\\'+v, trapvars[v])
        event = re.sub('\\'+v, trapvars[v], event)
        resource = re.sub('\\'+v, trapvars[v], resource)
        severity = re.sub('\\'+v, trapvars[v], severity)
        group = re.sub('\\'+v, trapvars[v], group)
        value = re.sub('\\'+v, trapvars[v], value)
        text = re.sub('\\'+v, trapvars[v], text)
        environment = re.sub('\\'+v, trapvars[v], environment)
        service = re.sub('\\'+v, trapvars[v], service)

    alertid = str(uuid.uuid4()) # random UUID

    headers = dict()
    headers['type']           = "snmptrapAlert"
    headers['correlation-id'] = alertid
    headers['persistent']     = 'true'
    headers['expires']        = int(time.time() * 1000) + EXPIRATION_TIME * 1000

    alert = dict()
    alert['id']               = alertid
    alert['resource']         = (environment + '.' + service + '.' + resource).lower()
    alert['event']            = event
    alert['group']            = group
    alert['value']            = value
    alert['severity']         = severity.upper()
    alert['severityCode']     = SEVERITY_CODE[alert['severity']]
    alert['environment']      = environment.upper()
    alert['service']          = service
    alert['text']             = text
    alert['type']             = 'snmptrapAlert'
    alert['tags']             = list() # FIXME - should be set somewhere above
    alert['summary']          = '%s - %s %s is %s on %s %s' % (environment, severity.upper(), event, value, service, resource)
    alert['createTime']       = datetime.datetime.utcnow().isoformat()+'Z'
    alert['origin']           = 'alert-snmptrap/%s' % os.uname()[1]
    alert['thresholdInfo']    = 'n/a'
    alert['correlatedEvents'] = correlate

    logging.info('%s : %s', alertid, json.dumps(alert))

    try:
        conn = stomp.Connection(BROKER_LIST)
        conn.start()
        conn.connect(wait=True)
    except Exception, e:
        print >>sys.stderr, "ERROR: Could not connect to broker - %s" % e
        logging.error('Could not connect to broker %s', e)
        sys.exit(1)
    try:
        conn.send(json.dumps(alert), headers, destination=ALERT_QUEUE)
    except Exception, e:
        print >>sys.stderr, "ERROR: Failed to send alert to broker - %s " % e
        logging.error('Failed to send alert to broker %s', e)
        sys.exit(1)
    conn.disconnect()
    sys.exit(0)
    
    logging.info('%s : Trap forwarded to %s', alertid, ALERT_QUEUE)

if __name__ == '__main__':
    main()

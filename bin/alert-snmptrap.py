#!/usr/bin/env python

########################################
#
# alert-snmptrap.py - Alert SNMP Trap Script
#
########################################

# See http://pysnmp.sourceforge.net/examples/2.x/snmptrap.html

import os
import sys
import optparse
try:
    import json
except ImportError:
    import simplejson as json
from optparse import OptionParser
import stomp
import time
import datetime
import logging
import uuid
import re

__version__ = '1.0'

BROKER_LIST  = [('devmonsvr01',61613), ('localhost', 61613)] # list of brokers for failover
ALERT_QUEUE  = '/queue/alerts'
EXPIRATION_TIME = 600 # seconds = 10 minutes

LOGFILE = '/var/log/alerta/alert-snmptrap.log'

def getEnv(line):

    env = {
        # '': 'PROD',
        'rel': 'REL',
        'qa' : 'QA',
        'tst': 'TEST',
        'cod': 'CODE',
        'stg': 'STAGE',
        'dev': 'DEV',
        'lwp': 'LWP'
    }

    m = re.match(r'.*(pools|monitors)/(?P<env>rel|qa|tst|cod|stg|dev|lwp)', line)
    if m:
        return env[m.group('env')]
    m = re.match(r'.*[N|n]ode \'?(?P<env>rel|qa|tst|cod|stg|dev|lwp)', line)
    if m:
        return env[m.group('env')]
    m = re.match(r'.*servers/vs_\w+.gu(?P<env>rel|qa|tst|cod|stg|dev|lwp)', line)
    if m:
        return env[m.group('env')]

    return 'INFRA'
        
def main():

    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s alert-snmptrap[%(process)d] %(levelname)s - %(message)s", filename=LOGFILE)

    rawData = sys.stdin.read()
    recv = rawData.split('\n')
    logging.info('trap -> %s', json.dumps(recv))

    # Parse the trap info
    agent      = recv[0].strip().split('.')[0]
    ip         = recv[1].strip()
    uptime     = recv[2].strip()
    trapoid    = recv[3].strip().split()[1]
    trapnumber = trapoid.rpartition('.')[2]
    payload    = recv[4].partition(' ')[2].strip().lstrip('\"').rstrip('\"')
    logging.info('agent %s trapoid %s payload %s', agent, trapoid, payload)

    # Defaults
    environment = 'INFRA'
    service     = 'Network'
    resource    = agent
    event       = trapoid
    group       = 'SNMP'
    severity    = 'WARNING'
    value       = 'unmatched'
    text        = payload

    # ZXTM Lookup (this will go into a config file eventually)
    zxtmTraps = {
         # Test Action
         "1":   { "event": "ZxtmTrap", "value": "TestAction", "severity": "NORMAL" }, # testaction
         # General
         "2":   { "event": "ZxtmSoftware", "value": "Running", "severity": "NORMAL" }, # running
         "3":   { "event": "ZxtmFreeFds", "value": "Not Many", "severity": "MINOR" }, # fewfreefds
         "4":   { "event": "ZxtmSoftware", "value": "Restart Required", "severity": "WARNING" }, # restartrequired
         "5":   { "event": "ZxtmTime", "value": "Moved Back", "severity": "WARNING" }, # timemovedback
         "6":   { "event": "ZxtmSSL", "value": "Failed", "severity": "WARNING" }, # sslfail     XXX - prod alert
         "7":   { "event": "ZxtmHardware", "value": "Notification", "severity": "WARNING" }, # hardware
         "8":   { "event": "ZxtmSoftware", "value": "Error", "severity": "WARNING" }, # zxtmswerror
         "9":   { "event": "ZxtmEvent", "value": "Custom", "severity": "WARNING" }, # customevent -- FIXME customEventName contained in trap payload
         "10":  { "event": "ZxtmSoftware", "value": "Version Mismatch", "severity": "WARNING" }, # versionmismatch
         "114": { "event": "ZxtmAuth", "value": "Error", "severity": "WARNING" }, # autherror
         # Fault Tolerance
         "11": { "event": "ZxtmMachine", "value": "OK", "severity": "NORMAL" },    # machineok
         "12": { "event": "ZxtmMachine", "value": "Timeout", "severity": "MAJOR" },    # machinetimeout      XXX - prod alert
         "13": { "event": "ZxtmMachine", "value": "Fail", "severity": "CRITICAL" },    # machinefail         XXX - prod alert
         "14": { "event": "ZxtmMachine", "value": "All OK", "severity": "NORMAL" },    # allmachinesok
         "15": { "event": "ZxtmFlipper", "value": "Backends Working", "severity": "NORMAL" },    # flipperbackendsworking
         "16": { "event": "ZxtmFlipper", "value": "Frontends Working", "severity": "NORMAL" },    # flipperfrontendsworking
         "17": { "event": "ZxtmPing", "value": "Backend Fail", "severity": "MINOR" },    # pingbackendfail     XXX - prod alert
         "18": { "event": "ZxtmPing", "value": "Frontend Fail", "severity": "MINOR" },    # pingfrontendfail   XXX - prod alert
         "19": { "event": "ZxtmPing", "value": "Gateway Fail", "severity": "MINOR" },    # pinggwfail          XXX - prod alert
         "20": { "event": "ZxtmState", "value": "Bad Data", "severity": "WARNING" },    # statebaddata         XXX - prod alert
         "21": { "event": "ZxtmState", "value": "Connection Failed", "severity": "MINOR" },    # stateconnfail XXX - prod alert
         "22": { "event": "ZxtmState", "value": "OK", "severity": "NORMAL" },    # stateok
         "23": { "event": "ZxtmState", "value": "Read Failed", "severity": "WARNING" },    # statereadfail     XXX - prod alert
         "24": { "event": "ZxtmState", "value": "Timeout", "severity": "WARNING" },    # statetimeout          XXX - prod alert
         "25": { "event": "ZxtmState", "value": "Unexpected", "severity": "WARNING" },    # stateunexpected    XXX - prod alert
         "26": { "event": "ZxtmState", "value": "Write Failed", "severity": "WARNING" },    # statewritefail   XXX - prod alert

         "107": { "event": "ZxtmActivate", "value": "All Dead", "severity": "CRITICAL" },    # activatealldead
         "108": { "event": "ZxtmMachine", "value": "Recovered", "severity": "NORMAL" },    # machinerecovered
         "109": { "event": "ZxtmFlipper", "value": "Recovered", "severity": "NORMAL" },    # flipperrecovered
         "110": { "event": "ZxtmActivate", "value": "Automatic", "severity": "WARNING" },    # activedautomatically
         "111": { "event": "ZxtmCluster", "value": "Module Error", "severity": "WARNING" },    # zclustermoderr  XXX - prod alert
         # XXX - skip EC2 traps 112-113,130-132
         "133": { "event": "ZxtmHostLoad", "value": "Changed", "severity": "WARNING" },    # multihostload
         # SSL hardware
         # XXX - skipped
         # Configuration files
         "30": { "event": "ZxtmConfig", "value": "File Deleted", "severity": "WARNING" },    # confdel
         "31": { "event": "ZxtmConfig", "value": "File Modified", "severity": "WARNING" },    # confmod
         "32": { "event": "ZxtmConfig", "value": "File Added", "severity": "WARNING" },    # confadd
         "33": { "event": "ZxtmConfig", "value": "File OK", "severity": "NORMAL" },    # confok
         "178": { "event": "ZxtmConfigRepl", "value": "Timeout", "severity": "WARNING" },    # confreptimeout
         "179": { "event": "ZxtmConfigRepl", "value": "Failed", "severity": "MINOR" },    # confrepfailed
         # Java
         # XXX - skipped
         # Monitors
         "41": { "event": "ZxtmMonitor", "value": "Failed", "severity": "WARNING" },    # monitorfail
         "42": { "event": "ZxtmMonitor", "value": "OK", "severity": "NORMAL" },    # monitorok
         # Rules
         # XXX - skipped
         "51": { "event": "ZxtmRule", "value": "Info", "severity": "NORMAL" },    # rulemsginfo
         # XXX - skipped
         # GLB Service Rules
         # XXX - skipped
         # License keys
         # XXX - skipped
         # Pools
         "64": { "event": "ZxtmPool", "value": "No Nodes", "severity": "CRITICAL" },    # poolnonodes
         "65": { "event": "ZxtmPool", "value": "OK", "severity": "NORMAL" } ,        # poolok
         "66": { "event": "ZxtmPool", "value": "Dead", "severity": "MAJOR" } ,      # pooldied                 XXX - prod alert
         # XXX - skipped
         # Traffic IPs
         "78": { "event": "ZxtmTIP", "value": "Drop IP", "severity": "WARNING" } ,      # dropipwarn                 XXX - prod alert
         "80": { "event": "ZxtmFlipper", "value": "IP Exists", "severity": "WARNING" } ,      # flipperipexists            XXX - prod alert
         # XXX - skipped
         # Service protection
         # XXX - skipped
         # SLM
         # XXX - skipped
         # Virtual servers
         "91": { "event": "ZxtmSSL", "value": "Drop", "severity": "MAJOR" } ,      # ssldrop                 XXX - prod alert
         # XXX - skipped
         # GLB
         # XXX - skipped
         # Other
         "104": { "event": "ZxtmConn", "value": "Error", "severity": "MINOR" } ,      # connerror                 XXX - prod alert
         "105": { "event": "ZxtmConn", "value": "Fail", "severity": "MAJOR" } ,      # connfail                 XXX - prod alert
         # XXX - skipped
    }

    #
    # Zeus ZXTM
    #
    if trapoid.startswith('SNMPv2-SMI::enterprises.7146'):
        group = 'ZXTM'
        if trapnumber in zxtmTraps:
            event = zxtmTraps[trapnumber]['event']
            value = zxtmTraps[trapnumber]['value']
            severity = zxtmTraps[trapnumber]['severity']
        else:
            event = 'ZxtmTrap'+trapnumber
            value = 'unmatched'
            if payload.startswith('INFO'):
                severity = 'NORMAL'
            elif payload.startswith('WARN'):
                severity = 'WARNING'
            elif payload.startswith('SERIOUS'):
                severity = 'MAJOR'
        environment = getEnv(payload)
        service = 'Network' # XXX - could we programatically determine the specific service eg. R1, R2, etc? do we care?
        logging.info('Suppressing ZXTM alerts for now!!!!!')
        sys.exit()

    alertid = str(uuid.uuid4()) # random UUID

    headers = dict()
    headers['type']           = "snmptrapAlert"
    headers['correlation-id'] = alertid
    headers['persistent']     = 'true'
    headers['expires']        = int(time.time() * 1000) + EXPIRATION_TIME * 1000

    alert = dict()
    alert['id']          = alertid
    alert['resource']    = (environment + '.' + service + '.' + resource).lower()
    alert['event']       = event
    alert['group']       = group
    alert['value']       = value
    alert['severity']    = severity.upper()
    alert['environment'] = environment.upper()
    alert['service']     = service
    alert['text']        = text
    alert['type']        = 'snmptrapAlert'
    alert['tags']        = list() # FIXME - should be set somewhere above
    alert['summary']     = '%s - %s %s is %s on %s %s' % (environment, severity, event, value, service, resource)
    alert['createTime']  = datetime.datetime.utcnow().isoformat()+'+00:00'
    alert['origin']      = 'alert-snmptrap/%s' % os.uname()[1]
    alert['rawData']     = rawData

    logging.info('ALERT: %s', json.dumps(alert))
    try:
        conn = stomp.Connection(BROKER_LIST)
        conn.start()
        conn.connect(wait=True)
    except Exception, e:
        print >>sys.stderr, "ERROR: Could not connect to broker - %s" % e
        logging.error('ERROR: Could not connect to broker %s', e)
        sys.exit(1)
    try:
        conn.send(json.dumps(alert), headers, destination=ALERT_QUEUE)
    except Exception, e:
        print >>sys.stderr, "ERROR: Failed to send alert to broker - %s " % e
        logging.error('ERROR: Failed to send alert to broker %s', e)
        sys.exit(1)
    conn.disconnect()
    print alertid
    sys.exit(0)
    
    logging.info('%s : Trap forwarded to %s', alertid, ALERT_QUEUE)

if __name__ == '__main__':
    main()

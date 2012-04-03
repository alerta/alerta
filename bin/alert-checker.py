#!/usr/bin/env python

########################################
#
# alert-checker.py - Alert Nagios Check
#
# Written by Nick Satterly (Mar 2012)
# 
########################################

import os
import sys
import optparse
try:
    import json
except ImportError:
    import simplejson as json
from optparse import OptionParser
import stomp
import subprocess
import shlex
import time
import datetime
import logging
import uuid
import re

__version__ = '1.1'

BROKER_LIST  = [('devmonsvr01',61613), ('localhost', 61613)] # list of brokers for failover
ALERT_QUEUE  = '/queue/alerts'
EXPIRATION_TIME = 600 # seconds = 10 minutes
NAGIOS_PLUGINS = '/usr/lib64/nagios/plugins'

LOGFILE = '/var/log/alerta/alert-checker.log'

# Command-line options
parser = optparse.OptionParser(version="%prog " + __version__, description="Alert Nagios Check - runs a Nagios plug-in and sends the result to the alerting system. Alerts have a resource (including service and environment), event name, value and text. A severity of 'normal' is used if none given. Tags and group are optional.", epilog='alert-checker.py --nagios "check_procs -w 10 -c 20 --metric=CPU" --resource Sever1 --event ProcStatus --group OS --env PROD --svc Discussion')
parser.add_option("-n", "--nagios", dest="nagios", help="Nagios check command line")
parser.add_option("-r", "--resource", dest="resource", help="Resource under alarm eg. hostname, network device, application. Note: ENVIRONMENT and SERVICE are prepended to the supplied RESOURCE")
parser.add_option("-e", "--event", dest="event", help="Event name eg. HostAvail, PingResponse, AppStatus")
parser.add_option("-g", "--group", dest="group", help="Event group eg. Application, Backup, Database, HA, Hardware, Job, Network, OS, Performance, Security")
parser.add_option("-E", "--environment", dest="environment", help="Environment eg. PROD, REL, QA, TEST, CODE, STAGE, DEV, LWP, INFRA")
parser.add_option("-S", "--svc", "--service", dest="service", help="Service eg. R1, R2, Discussion, Soulmates, ContentAPI, MicroApp, FlexibleContent, Mutualisation, SharedSvcs")
parser.add_option("-T", "--tag", action="append", dest="tags", help="Tag the event with anything and everything.")
parser.add_option("-d", "--dry-run", action="store_true", default=False, help="Do not send alert.")

VALID_SEVERITY    = [ 'CRITICAL','MAJOR','MINOR','WARNING','NORMAL','INFORM', 'DEBUG' ]
VALID_ENVIRONMENT = [ 'PROD', 'REL', 'QA', 'TEST', 'CODE', 'STAGE', 'DEV', 'LWP','INFRA' ]
VALID_SERVICES    = [ 'R1', 'R2', 'Discussion', 'Soulmates', 'ContentAPI', 'MicroApp', 'FlexibleContent', 'Mutualisation', 'SharedSvcs' ]

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

options, args = parser.parse_args()

if not options.resource:
    parser.print_help()
    parser.error("Must supply event resource using -r or --resource")

if not options.event:
    parser.print_help()
    parser.error("Must supply event name using -e or --event")

if not options.group:
    options.group = 'Misc'

if options.environment not in VALID_ENVIRONMENT:
    parser.print_help()
    parser.error("Environment must be one of %s" % ','.join(VALID_ENVIRONMENT))

if options.service not in VALID_SERVICES:
    parser.print_help()
    parser.error("Service must be one of %s" % ','.join(VALID_SERVICES))

if not options.nagios:
    parser.print_help()
    parser.error("Must supply full command line for Nagios check using -n or --nagios")

def main():

    logging.basicConfig(level=logging.INFO, format="%(asctime)s alert-checker[%(process)d] %(levelname)s - %(message)s", filename=LOGFILE)

    # Run Nagios plugin check
    args = shlex.split(os.path.join(NAGIOS_PLUGINS, options.nagios))
    logging.info('Running %s', args)
    check = subprocess.Popen(args, stdout=subprocess.PIPE)
    stdout = check.communicate()[0]
    rc = check.returncode

    # Parse Nagios plugin check output
    if rc == 0:
        severity = 'NORMAL'
    elif rc == 1:
        severity = 'WARNING'
    elif rc == 2:
        severity = 'CRITICAL'
    elif rc == 3:
        severity = 'INFORM' # XXX - aka UNKNOWN

    m = re.match(r'(?P<value>.*)\s*[-|:]', stdout)
    if m:
        value = m.group('value')
    else:
        value = 'unmatched'
    text = stdout.strip()

    alertid = str(uuid.uuid4()) # random UUID
    logging.info('%s : Nagios plugin %s => %s (rc=%d)', alertid, options.nagios, text, rc)

    headers = dict()
    headers['type']           = "exceptionAlert"
    headers['correlation-id'] = alertid
    headers['persistent']     = 'true'
    headers['expires']        = int(time.time() * 1000) + EXPIRATION_TIME * 1000

    alert = dict()
    alert['id']            = alertid
    alert['resource']      = (options.environment + '.' + options.service + '.' + options.resource).lower()
    alert['event']         = options.event
    alert['group']         = options.group
    alert['value']         = value
    alert['severity']      = severity
    alert['severityCode']  = SEVERITY_CODE[alert['severity']]
    alert['environment']   = options.environment.upper()
    alert['service']       = options.service
    alert['text']          = text
    alert['type']          = 'exceptionAlert'
    alert['tags']          = options.tags
    alert['summary']       = '%s - %s %s is %s on %s %s' % (options.environment, severity, options.event, value, options.service, options.resource)
    alert['createTime']    = datetime.datetime.utcnow().isoformat()+'+00:00'
    alert['origin']        = 'alert-checker/%s' % os.uname()[1]
    alert['thresholdInfo'] = options.nagios

    logging.info('%s : %s', alertid, json.dumps(alert))

    if (not options.dry_run):
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
        broker = conn.get_host_and_port()
        logging.info('%s : Alert sent to %s:%s', alertid, broker[0], str(broker[1]))
        conn.disconnect()
        print alertid
        sys.exit(0)
    else:
        print "%s %s" % (json.dumps(headers,indent=4), json.dumps(alert,indent=4))

if __name__ == '__main__':
    main()

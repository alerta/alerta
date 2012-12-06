#!/usr/bin/env python

########################################
#
# alert-sender.py - Alert Command-line script
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
try:
    import stomp
except ImportError:
    print >>sys.stderr, 'ERROR: You need to install the stomp python module'
    sys.exit(1)
import time
import datetime
import logging
import uuid

__program__ = 'alert-sender'
__version__ = '1.1.3'

BROKER_LIST  = [('monitoring.guprod.gnl', 61613),('localhost', 61613)] # list of brokers for failover
ALERT_QUEUE  = '/queue/alerts'

DEFAULT_TIMEOUT = 86400
EXPIRATION_TIME = 600 # seconds = 10 minutes

LOGFILE = '/var/log/alerta/alert-sender.log'

# Command-line options
parser = optparse.OptionParser(
                  version="%prog " + __version__,
                  description="Alert Command-Line Tool - sends an alert to the alerting system. Alerts must have a resource (including service and environment), event name, value and text. A severity of 'normal' is used if none given. Tags and group are optional.",
                  epilog="alert-sender.py --resource myCoolApp --event AppStatus --group Application --value Down --severity critical --env PROD --svc MicroApp --tag release:134 --tag build:1005 --text 'Micro App X is down.'")
parser.add_option("-r",
                  "--resource",
                  dest="resource",
                  help="Resource under alarm eg. hostname, network device, application.")
parser.add_option("-e",
                  "--event",
                  dest="event",
                  help="Event name eg. HostAvail, PingResponse, AppStatus")
parser.add_option("-c",
                  "--correlate",
                  dest="correlate",
                  help="Comma-separated list of events to correlate together eg. NodeUp,NodeDown")
parser.add_option("-g",
                  "--group",
                  dest="group",
                  help="Event group eg. Application, Backup, Database, HA, Hardware, Job, Network, OS, Performance, Security")
parser.add_option("-v",
                  "--value",
                  dest="value",
                  help="Event value eg. 100%, Down, PingFail, 55tps, ORA-1664")
parser.add_option("-s",
                  "--severity",
                  dest="severity",
                  help="Severity eg. Critical, Major, Minor, Warning, Normal, Inform")
parser.add_option("-E",
                  "--environment",
                  action="append",
                  dest="environment",
                  help="Environment eg. PROD, REL, QA, TEST, CODE, STAGE, DEV, LWP, INFRA")
parser.add_option("-S",
                  "--svc",
                  "--service",
                  action="append",
                  dest="service",
                  help="Service eg. R1, R2, Discussion, Soulmates, ContentAPI, MicroApp, FlexibleContent, Mutualisation, SharedSvcs")
parser.add_option("-T",
                  "--tag",
                  action="append",
                  dest="tags",
                  default=list(),
                  help="Tag the event with anything and everything.")
parser.add_option("-t",
                  "--text",
                  dest="text",
                  help="Freeform alert text eg. Host not responding to ping.")
parser.add_option("-o",
                  "--timeout",
                  type=int,
                  dest="timeout",
                  default=DEFAULT_TIMEOUT,
                  help="Timeout in seconds that OPEN alert will persist in console.")
parser.add_option("-H",
                  "--heartbeat",
                  action="store_true",
                  default=False,
                  help="Send heartbeat to alerta.")
parser.add_option("-O",
                  "--origin",
                  dest="origin",
                  help="Origin of heartbeat. Usually an application instance.")
parser.add_option("-q",
                  "--quiet",
                  action="store_true",
                  default=False,
                  help="Do not display alert id.")
parser.add_option("-d",
                  "--dry-run",
                  action="store_true",
                  default=False,
                  help="Do not send alert.")

VALID_SEVERITY    = [ 'CRITICAL', 'MAJOR', 'MINOR', 'WARNING', 'NORMAL', 'INFORM', 'DEBUG' ]
VALID_ENVIRONMENT = [ 'PROD', 'REL', 'QA', 'TEST', 'CODE', 'STAGE', 'DEV', 'LWP','INFRA' ]

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

def send_message(alert, headers):

    logging.info('%s : %s', alert['id'], json.dumps(alert))

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
        logging.info('%s : Alert sent to %s:%s', alert['id'], broker[0], str(broker[1]))
        conn.disconnect()
        if not options.quiet:
            print alert['id']
        sys.exit(0)
    else:
        print "%s %s" % (json.dumps(headers, indent=4), json.dumps(alert, indent=4))
    sys.exit(0)

# main()
options, args = parser.parse_args()

if options.heartbeat:
    if not options.origin:
        parser.error("Must supply origin to send a heartbeat.")

    heartbeatid = str(uuid.uuid4()) # random UUID
    createTime = datetime.datetime.utcnow()

    headers = dict()
    headers['type']           = "heartbeat"
    headers['correlation-id'] = heartbeatid

    heartbeat = dict()
    heartbeat['id']         = heartbeatid
    heartbeat['type']       = "heartbeat"
    heartbeat['createTime'] = createTime.replace(microsecond=0).isoformat() + ".%03dZ" % (createTime.microsecond//1000)
    heartbeat['origin']     = "%s/%s" % (options.origin,os.uname()[1])
    if options.tags:
        heartbeat['version'] = options.tags
    else:
        heartbeat['version'] = __version__

    send_message(heartbeat, headers)

if not options.resource:
    parser.print_help()
    parser.error("Must supply event resource using -r or --resource")

if not options.event:
    parser.print_help()
    parser.error("Must supply event name using -e or --event")

if not options.group:
    options.group = 'Misc'

if not options.value:
    parser.print_help()
    parser.error("Must supply event value using -v or --value")

if not options.severity:
    options.severity = 'normal'
elif options.severity.upper() not in VALID_SEVERITY:
    parser.print_help()
    parser.error("Severity '%s' must be one of %s" % (options.severity, ','.join(VALID_SEVERITY)))

if not all(x in VALID_ENVIRONMENT for x in options.environment):
    parser.print_help()
    parser.error("Must supply one or more environments from %s" % ','.join(VALID_ENVIRONMENT))
else:
    options.environment = [x.upper() for x in options.environment]

if not options.service:
    parser.print_help()
    parser.error("Must supply one or more service using -S or --service")

if not options.text:
    parser.print_help()
    parser.error("Must supply alert text. How else are we to know what happened?")

    try:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s alert-sender[%(process)d] %(levelname)s - %(message)s", filename=LOGFILE)
    except IOError:
        pass

else:
    alertid = str(uuid.uuid4()) # random UUID
    createTime = datetime.datetime.utcnow()

    headers = dict()
    headers['type']           = "exceptionAlert"
    headers['correlation-id'] = alertid

    alert = dict()
    alert['id']            = alertid
    alert['resource']      = options.resource
    alert['event']         = options.event
    if options.correlate:
        alert['correlatedEvents'] = options.correlate.split(',')
    alert['group']         = options.group
    alert['value']         = options.value
    alert['severity']      = options.severity.upper()
    alert['severityCode']  = SEVERITY_CODE[alert['severity']]
    alert['environment']   = options.environment
    alert['service']       = options.service
    alert['text']          = options.text
    alert['type']          = 'exceptionAlert'
    alert['tags']          = options.tags
    alert['summary']       = '%s - %s %s is %s on %s %s' % (','.join(options.environment), options.severity.upper(), options.event, options.value, ','.join(options.service), options.resource)
    alert['createTime']    = createTime.replace(microsecond=0).isoformat() + ".%03dZ" % (createTime.microsecond//1000)
    alert['origin']        = "%s/%s" % (__program__, os.uname()[1])
    alert['thresholdInfo'] = 'n/a'
    alert['timeout']       = options.timeout

    send_message(alert, headers)

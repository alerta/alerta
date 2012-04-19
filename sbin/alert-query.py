#!/usr/bin/env python
########################################
#
# alert-query.py - Alert query tool
#
########################################

import os
import sys
from optparse import OptionParser
import datetime
import pymongo
import operator
import pytz

__version__ = '1.0.4'

SEV = {
    'CRITICAL': 'Crit',
    'MAJOR':    'Majr',
    'MINOR':    'Minr',
    'WARNING':  'Warn',
    'NORMAL':   'Norm',
    'INFORM':   'Info', 
    'DEBUG':    'Dbug',
}

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

COLOR = {
    'CRITICAL': '\033[91m',
    'MAJOR':    '\033[95m',
    'MINOR':    '\033[93m',
    'WARNING':  '\033[96m',
    'NORMAL':   '\033[92m',
    'INFORM':   '\033[92m',
    'DEBUG':    '\033[90m',
}
ENDC     = '\033[0m'

ORDERBY = {
    'environment':     ('environment', pymongo.DESCENDING),
    'service':         ('service', pymongo.DESCENDING),
    'resource':        ('resource', pymongo.DESCENDING),
    'event':           ('event', pymongo.DESCENDING),
    'group':           ('group', pymongo.DESCENDING),
    'value':           ('history.value', pymongo.DESCENDING),
    'severity':        ('history.severityCode', pymongo.DESCENDING),
    'text':            ('history.text', pymongo.DESCENDING),
    'type':            ('type', pymongo.DESCENDING),
    'createTime':      ('history.createTime', pymongo.DESCENDING),
    'receiveTime':     ('history.receiveTime', pymongo.DESCENDING),
    'lastReceiveTime': ('lastReceiveTime', pymongo.DESCENDING),
    'origin':          ('origin', pymongo.DESCENDING),
    'thresholdInfo':   ('thresholdInfo', pymongo.DESCENDING)
}

# Defaults
PGM='alert-query.py'
SERVER='localhost'
TIMEZONE='Europe/London'
DATE_FORMAT = '%d/%m/%y %H:%M:%S'

def main():

    # Command-line options
    parser = OptionParser(
                      version="%prog " + __version__, 
                      description="Alert database query tool - show alerts filtered by attributes",
                      epilog="alert-query.py --color --env 'QA|REL' --group Puppet --count 10 --show all")
    parser.add_option("-m",
                      "--server",
                      dest="server",
                      help="MongoDB server (default: localhost)")
    parser.add_option("-z",
                      "--timezone",
                      dest="timezone",
                      help="Set timezone (default: Europe/London)")
    parser.add_option("--minutes",
                      "--mins",
                      type="int",
                      dest="minutes",
                      help="Show alerts for last <x> minutes")
    parser.add_option("--hours",
                      "--hrs",
                      type="int",
                      dest="hours",
                      help="Show alerts for last <x> hours")
    parser.add_option("--days",
                      type="int",
                      dest="days",
                      help="Show alerts for last <x> days")
    parser.add_option("-i",
                      "--id",
                      dest="alertid",
                      help="Alert ID (can use 8-char abbrev id)")
    parser.add_option("-E",
                      "--environment",
                      dest="environment",
                      help="Environment eg. PROD, REL, QA, TEST, CODE, STAGE, DEV, LWP, INFRA")
    parser.add_option("-S",
                      "--svc",
                      "--service",
                      dest="service",
                      help="Service eg. R1, R2, Discussion, Soulmates, ContentAPI, MicroApp, FlexibleContent, Mutualisation, SharedSvcs")
    parser.add_option("-r",
                      "--resource",
                      dest="resource",
                      help="Resource under alarm eg. hostname, network device, application")
    parser.add_option("-s",
                      "--severity",
                      dest="severity",
                      help="Severity or range eg. major, warning..critical")
    parser.add_option("-e",
                      "--event",
                      dest="event",
                      help="Event name eg. HostAvail, PingResponse, AppStatus")
    parser.add_option("-g",
                      "--group",
                      dest="group",
                      help="Event group eg. Application, Backup, Database, HA, Hardware, Job, Network, OS, Performance, Security")
    parser.add_option("-v",
                      "--value",
                      dest="value",
                      help="Event value eg. 100%, Down, PingFail, 55tps, ORA-1664")
    parser.add_option("-t",
                      "--text",
                      dest="text")
    parser.add_option("--show",
                      action="append",
                      dest="show",
                      default=[],
                      help="Show 'text', 'times', 'details', 'tags' and 'color'")
    parser.add_option("-o",
                      "--orderby",
                      "--sort",
                      dest="orderby",
                      help="Order by attribute (default: createTime)")
    parser.add_option("-c",
                      "--count",
                      "--limit",
                      type="int",
                      dest="limit",
                      default=0)
    parser.add_option( "--no-header",
                      action="store_true",
                      dest="noheader")
    parser.add_option( "--no-footer",
                      action="store_true",
                      dest="nofooter")
    parser.add_option("--color",
                      "--colour",
                      action="store_true",
                      default=False,
                      help="Synonym for --show=color")
    parser.add_option("-d",
                      "--dry-run",
                      action="store_true",
                      default=False,
                      help="Do not run. Output query and filter.")
    options, args = parser.parse_args()

    if options.server:
        server = options.server
    else:
        server = SERVER

    # Connect to MongoDB
    try:
        mongo = pymongo.Connection(server)
        db = mongo.monitoring
        alerts = db.alerts
    except pymongo.errors.ConnectionFailure, e:
        print >>sys.stderr, "ERROR: Connection to MongoDB %s failed" % server
        sys.exit(1)

    query = dict()
    minutes = 0
    hours = 0
    days = 0
    num_regex = 0
    if options.minutes:
        minutes = options.minutes
    if options.hours:
        hours = options.minutes
    if options.days:
        days = options.days
    if options.alertid:
        # Example - db.alerts.findOne({$or: [{'lastReceiveId': {'$regex': '^b8d05b47'}}, { 'history.id': {'$regex': '^b8d05b47'}} ] });
        query['$or'] = list()
        query['$or'].append({ 'history.id': { '$regex': '^'+options.alertid } } )
        query['$or'].append({ 'lastReceiveId': { '$regex': '^'+options.alertid } } )
        num_regex += 2
    if options.environment:
        query['environment'] = { '$regex': options.environment }
        num_regex += 1
    if options.service:
        query['service'] = { '$regex': options.service }
        num_regex += 1
    if options.resource:
        query['resource'] = { '$regex': options.resource }
        num_regex += 1
    if options.severity:
        m = options.severity.split('..')
        if len(m) > 1:
            query['severityCode'] = { '$lte': SEVERITY_CODE[m[0].upper()], '$gte': SEVERITY_CODE[m[1].upper()] }
        else:
            query['severityCode'] = SEVERITY_CODE[options.severity.upper()]
    if options.event:
        query['event'] = { '$regex': options.event }
        num_regex += 1
    if options.group:
        query['group'] = { '$regex': options.group }
        num_regex += 1
    if options.value:
        query['history.value'] = { '$regex': options.value }
        num_regex += 1
    if options.text:
        query['history.text'] = { '$regex': options.text }
        num_regex += 1

    if num_regex > 4:
        print "ERROR: Too many regexes in query (limit is 4 until v2.1.0)"
        # see https://jira.mongodb.org/browse/SERVER-969
        sys.exit(1)

    if minutes or hours or days:
        end = datetime.datetime.utcnow()
        end = end.replace(tzinfo=pytz.utc)
        start = end - datetime.timedelta(days=days, minutes=minutes+hours*60)
        start = start.replace(tzinfo=pytz.utc)
        if options.orderby in ['createTime', 'receiveTime', 'lastReceiveTime']:
            query[options.orderby] = {'$gte': start, '$lt': end}
        else:
            query['createTime'] = {'$gte': start, '$lt': end}

    fields = { "environment": 1, "service": 1,
        "resource": 1, "event": 1, "group": 1,
        "type": 1, "tags": 1, "origin": 1,
        "thresholdInfo": 1, "lastReceiveId": 1,
        "lastReceiveTime": 1 }
    if 'history' in options.show:
        fields['history'] = 1
    else:
        fields['history'] = { '$slice': -1 }

    orderby = list()
    if options.orderby:
        orderby.append(ORDERBY[options.orderby])
    else:
        orderby.append(('history.createTime', pymongo.DESCENDING))

    if options.limit:
        LIMIT = options.limit
    else:
        LIMIT = 0

    if options.dry_run:
        print "DEBUG: monitoring.alerts { $query: %s, $orderby: %s }" % (query, orderby)
        sys.exit(0)

    results = list()
    for alert in alerts.find(query, fields).sort(orderby).limit(LIMIT):
        for hist in alert['history']:
            results.append((alert['_id'],
                hist['id'],
                alert['lastReceiveId'],
                alert['environment'],
                alert['service'],
                alert['resource'],
                alert['event'],
                alert['group'],
                hist.get('value', 'n/a'),
                hist['severity'],
                hist['text'],
                alert['type'],
                alert['tags'],
                hist['createTime'].replace(tzinfo=pytz.utc),
                hist['receiveTime'].replace(tzinfo=pytz.utc),
                alert['lastReceiveTime'].replace(tzinfo=pytz.utc),
                alert['origin'],
                alert.get('thresholdInfo', 'n/a')))

    if not options.timezone:
        user_tz = TIMEZONE
    else:
        user_tz = options.timezone
    tz=pytz.timezone(user_tz)

    if not options.noheader:
        print "Alerta Report Tool"
        print "    database: %s" % server
        print "    timezone: %s" % user_tz
        if minutes or hours or days:
            print "    interval: %s - %s" % (start.astimezone(tz).strftime(DATE_FORMAT), end.astimezone(tz).strftime(DATE_FORMAT))
        if options.show:
            print "        show: %s" % ', '.join(options.show)
        if options.orderby:
            print "    order by: %s" % options.orderby
        if options.alertid:
            print "    alert id: ^%s" % options.alertid
        if options.environment:
            print " environment: %s" % options.environment
        if options.service:
            print "     service: %s" % options.service
        if options.resource:
            print "    resource: %s" % options.resource
        if options.severity:
            print "    severity: %s" % options.severity
        if options.event:
            print "       event: %s" % options.event
        if options.group:
            print "       group: %s" % options.group
        if options.value:
            print "       value: %s" % options.value
        if options.text:
            print "        text: %s" % options.text
        if options.limit:
            print "       count: %d" % LIMIT
        print

    if 'some' in options.show:
        options.show.append('text')
        options.show.append('details')
    elif 'all' in options.show:
        options.show.append('text')
        options.show.append('times')
        options.show.append('details')
        options.show.append('tags')

    line_color = ''
    end_color = ''
    if 'color' in options.show or options.color:
        end_color = ENDC

    count = 0
    results.reverse()
    for r in results:
        objectid        = r[0]
        alertid         = r[1]
        lastReceiveId   = r[2]
        environment     = r[3]
        service         = r[4]
        resource        = r[5]
        event           = r[6]
        group           = r[7]
        value           = r[8]
        severity        = r[9]
        text            = r[10]
        type            = r[11]
        tags            = r[12]
        createTime      = r[13]
        receiveTime     = r[14]
        latency         = receiveTime - createTime
        lastReceiveTime = r[15]
        origin          = r[16]
        thresholdInfo   = r[17]
        count += 1

        if options.orderby == 'receiveTime':
            displayTime = receiveTime
        elif options.orderby == 'lastReceiveTime':
            displayTime = lastReceiveTime
        else:
            displayTime = createTime

        if 'color' in options.show or options.color:
            line_color = COLOR[severity]
        print(line_color + '%s|%s|%s|%-18s|%12s|%16s|%12s' % (alertid[0:8],
            displayTime.astimezone(tz).strftime(DATE_FORMAT),
            SEV[severity],
            resource.split('.')[-1],
            group,
            event,
            value) + end_color)

        if 'text' in options.show:
            print(line_color + '   |%s' % (text) + end_color)

        if 'times' in options.show:
            print(line_color + '    time created  | %s' % (createTime.astimezone(tz).strftime(DATE_FORMAT)) + end_color)
            print(line_color + '    time received | %s' % (receiveTime.astimezone(tz).strftime(DATE_FORMAT)) + end_color)
            print(line_color + '    last received | %s' % (lastReceiveTime.astimezone(tz).strftime(DATE_FORMAT)) + end_color)
            print(line_color + '    latency       | %s' % (latency) + end_color)

        if 'details' in options.show:
            print(line_color + '        object id    | %s' % (objectid) + end_color)
            print(line_color + '        alert id     | %s' % (alertid) + end_color)
            print(line_color + '        last recv id | %s' % (lastReceiveId) + end_color)
            print(line_color + '        environment  | %s' % (environment) + end_color)
            print(line_color + '        service      | %s' % (service) + end_color)
            print(line_color + '        resource     | %s' % (resource) + end_color)
            print(line_color + '        type         | %s' % (type) + end_color)
            print(line_color + '        origin       | %s' % (origin) + end_color)
            print(line_color + '        threshold    | %s' % (thresholdInfo) + end_color)

        if 'tags' in options.show and tags:
            for t in tags:
                print(line_color + '            tag | %s' % (t) + end_color)

    if not options.nofooter:
        now = datetime.datetime.utcnow()
        now = now.replace(tzinfo=pytz.utc)
        print
        print "Total: %d (produced on %s at %s by %s,v%s on %s)" % (count, now.astimezone(tz).strftime("%d/%m/%y"), now.astimezone(tz).strftime("%H:%M:%S %Z"), PGM, __version__, os.uname()[1])

if __name__ == '__main__':
    main()

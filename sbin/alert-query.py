#!/usr/bin/env python
########################################
#
# alert-query.py - Alert query tool
#
########################################

import os
import sys
from optparse import OptionParser
import time
import datetime
try:
    import json
except ImportError:
    import simplejson
import urllib2
import operator
import pytz

__version__ = '1.2.3'

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

# Defaults
PGM='alert-query.py'
SERVER = 'monitoring.guprod.gnl'
TIMEZONE='Europe/London'
DATE_FORMAT = '%d/%m/%y %H:%M:%S'

def main():

    # Command-line options
    parser = OptionParser(
                      version="%prog " + __version__, 
                      description="Alert database query tool - show alerts filtered by attributes",
                      epilog="alert-query.py --color --env QA,REL --group Puppet --count 10 --show all")
    parser.add_option("-m",
                      "--server",
                      dest="server",
                      help="Alerta server (default: %s)" % SERVER)
    parser.add_option("-z",
                      "--timezone",
                      dest="timezone",
                      help="Set timezone (default: Europe/London)")
    parser.add_option("--minutes",
                      "--mins",
                      type="int",
                      dest="minutes",
                      default=0,
                      help="Show alerts for last <x> minutes")
    parser.add_option("--hours",
                      "--hrs",
                      type="int",
                      dest="hours",
                      default=0,
                      help="Show alerts for last <x> hours")
    parser.add_option("--days",
                      type="int",
                      dest="days",
                      default=0,
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
    parser.add_option( "--status",
                      dest="status",
                      help="Status eg. OPEN, ACK, CLOSED")
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
    parser.add_option("-T",
                      "--tags",
                      dest="tags")
    parser.add_option("-t",
                      "--text",
                      dest="text")
    parser.add_option("--show",
                      action="append",
                      dest="show",
                      default=[],
                      help="Show 'text', 'times', 'attributes', 'details', 'tags', 'counts' and 'color'")
    parser.add_option("-o",
                      "--orderby",
                      "--sortby",
                      "--sort-by",
                      dest="sortby",
                      default='lastReceiveTime',
                      help="Sort by attribute (default: createTime)")
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
    API_URL = 'http://%s/alerta/api/v1/alerts' % server

    query = list()

    if options.minutes or options.hours or options.days:
        now = datetime.datetime.utcnow()
        fromTime = now - datetime.timedelta(days=options.days, minutes=options.minutes+options.hours*60)
        query.append('from-date=%s' % fromTime.replace(microsecond=0).isoformat() + ".%03dZ" % (fromTime.microsecond//1000))
        now = now.replace(tzinfo=pytz.utc)
        fromTime = fromTime.replace(tzinfo=pytz.utc)

    if options.alertid:
        for o in options.alertid.split(','):
            query.append('id=%s' % o)

    if options.environment:
        for o in options.environment.split(','):
            query.append('environment=%s' % o)

    if options.service:
        for o in options.service.split(','):
            query.append('service=%s' % o)

    if options.resource:
        for o in options.resource.split(','):
            query.append('resource=%s' % o)

    if options.severity:
        for o in options.severity.split(','):
            query.append('severity=%s' % o)
#         m = options.severity.split('..')
#         if len(m) > 1:
#             query['severityCode'] = { '$lte': SEVERITY_CODE[m[0].upper()], '$gte': SEVERITY_CODE[m[1].upper()] }
#         else:
#             query['severityCode'] = SEVERITY_CODE[options.severity.upper()]

    if options.status:
        for o in options.status.split(','):
            query.append('status=%s' % o)

    if options.event:
        for o in options.event.split(','):
            query.append('event=%s' % o)

    if options.group:
        for o in options.group.split(','):
            query.append('group=%s' % o)

    if options.value:
        for o in options.value.split(','):
            query.append('value=%s' % o)

    if options.tags:
        for o in options.tags.split(','):
            query.append('tags=%s' % o)

    if options.text:
        for o in options.text.split(','):
            query.append('text=%s' % o)

    if options.sortby:
        query.append('sort-by=%s' % options.sortby)

    if options.limit:
        query.append('limit=%s' % options.limit)

    if options.show == ['counts']:
        query.append('hide-alert-details=true')

    url = "%s?%s" % (API_URL, '&'.join(query))

    if options.dry_run:
        print "DEBUG: %s" % (url)
        sys.exit(0)

    if not options.timezone:
        user_tz = TIMEZONE
    else:
        user_tz = options.timezone
    tz=pytz.timezone(user_tz)

    if not options.noheader:
        print "Alerta Report Tool"
        print "    database: %s" % server
        print "    timezone: %s" % user_tz
        if options.minutes or options.hours or options.days:
            print "    interval: %s - %s" % (fromTime.astimezone(tz).strftime(DATE_FORMAT), now.astimezone(tz).strftime(DATE_FORMAT))
        if options.show:
            print "        show: %s" % ', '.join(options.show)
        if options.sortby:
            print "     sort by: %s" % options.sortby
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
        if options.status:
            print "      status: %s" % options.status
        if options.event:
            print "       event: %s" % options.event
        if options.group:
            print "       group: %s" % options.group
        if options.value:
            print "       value: %s" % options.value
        if options.text:
            print "        text: %s" % options.text
        if options.limit:
            print "       count: %d" % options.limit
        print

    if 'some' in options.show:
        options.show.append('text')
        options.show.append('details')
    elif 'all' in options.show:
        options.show.append('text')
        options.show.append('attributes')
        options.show.append('times')
        options.show.append('details')
        options.show.append('tags')

    line_color = ''
    end_color = ''
    if 'color' in options.show or options.color:
        end_color = ENDC

    # Query API for alerts
    start = time.time()
    try:
        output = urllib2.urlopen(url).read()
        response = json.loads(output)['response']
    except urllib2.URLError, e:
        print "ERROR: Alert query %s failed - %s" % (url, e)
        sys.exit(1)
    end = time.time()

    if options.sortby in ['createTime', 'receiveTime', 'lastReceiveTime']:
        alertDetails = reversed(response['alerts']['alertDetails'])
    else:
        alertDetails = response['alerts']['alertDetails']

    count = 0
    for alert in alertDetails:
        alertid          = alert['id']
        correlatedEvents = alert.get('correlatedEvents', ['n/a'])
        createTime       = datetime.datetime.strptime(alert['createTime'], '%Y-%m-%dT%H:%M:%S.%fZ')
        createTime       = createTime.replace(tzinfo=pytz.utc)
        environment      = alert['environment']
        event            = alert['event']
        graphs           = alert.get('graphs', ['n/a'])
        group            = alert['group']
        moreInfo         = alert.get('moreInfo', 'n/a')
        origin           = alert['origin']
        resource         = alert['resource']
        service          = alert['service']
        severity         = alert['severity']
        severityCode     = int(alert['severityCode'])
        status           = alert['status']
        summary          = alert['summary']
        tags             = alert['tags']
        text             = alert['text']
        thresholdInfo    = alert.get('thresholdInfo', 'n/a')
        timeout          = alert.get('timeout', '0')
        type             = alert['type']
        value            = alert['value']

        duplicateCount   = int(alert['duplicateCount'])
        if alert['expireTime'] is not None:
            expireTime   = datetime.datetime.strptime(alert['expireTime'], '%Y-%m-%dT%H:%M:%S.%fZ')
            expireTime   = expireTime.replace(tzinfo=pytz.utc)
        else:
            expireTime   = None
        lastReceiveId    = alert['lastReceiveId']
        lastReceiveTime  = datetime.datetime.strptime(alert['lastReceiveTime'], '%Y-%m-%dT%H:%M:%S.%fZ')
        lastReceiveTime  = lastReceiveTime.replace(tzinfo=pytz.utc)
        previousSeverity = alert['previousSeverity']
        receiveTime      = datetime.datetime.strptime(alert['receiveTime'], '%Y-%m-%dT%H:%M:%S.%fZ')
        receiveTime      = receiveTime.replace(tzinfo=pytz.utc)
        repeat           = alert['repeat']
        delta            = receiveTime - createTime
        latency          = int(delta.days * 24 * 60 * 60 * 1000 + delta.seconds * 1000 + delta.microseconds / 1000)

        count += 1

        if options.sortby == 'createTime':
            displayTime = createTime
        elif options.sortby == 'receiveTime':
            displayTime = receiveTime
        else:
            displayTime = lastReceiveTime

        if 'color' in options.show or options.color:
            line_color = COLOR[severity]

        if 'summary' in options.show:
            print(line_color + '%s' % summary + end_color)
        else:
            print(line_color + '%s|%s|%s|%5d|%-5s|%-10s|%-18s|%12s|%16s|%12s' % (alertid[0:8],
                displayTime.astimezone(tz).strftime(DATE_FORMAT),
                SEV[severity],
                duplicateCount,
                environment,
                service,
                resource.split('.')[-1],
                group,
                event,
                value) + end_color)

        if 'text' in options.show:
            print(line_color + '   |%s' % (text) + end_color)

        if 'attributes' in options.show:
            print(line_color + '    severity | %s -> %s (%s)' % (previousSeverity, severity, severityCode) + end_color)
            print(line_color + '    status   | %s' % (status) + end_color)
            print(line_color + '    resource | %s' % (resource) + end_color)
            print(line_color + '    group    | %s' % (group) + end_color)
            print(line_color + '    event    | %s' % (event) + end_color)
            print(line_color + '    value    | %s' % (value) + end_color)

        if 'times' in options.show:
            print(line_color + '      time created  | %s' % (createTime.astimezone(tz).strftime(DATE_FORMAT)) + end_color)
            print(line_color + '      time received | %s' % (receiveTime.astimezone(tz).strftime(DATE_FORMAT)) + end_color)
            print(line_color + '      last received | %s' % (lastReceiveTime.astimezone(tz).strftime(DATE_FORMAT)) + end_color)
            print(line_color + '      latency       | %sms' % (latency) + end_color)
            print(line_color + '      timeout       | %ss' % (timeout) + end_color)
            if expireTime:
                print(line_color + '      expire time   | %s' % (expireTime.astimezone(tz).strftime(DATE_FORMAT)) + end_color)

        if 'details' in options.show:
            print(line_color + '          alert id     | %s' % (alertid) + end_color)
            print(line_color + '          last recv id | %s' % (lastReceiveId) + end_color)
            print(line_color + '          environment  | %s' % (environment) + end_color)
            print(line_color + '          service      | %s' % (service) + end_color)
            print(line_color + '          resource     | %s' % (resource) + end_color)
            print(line_color + '          type         | %s' % (type) + end_color)
            print(line_color + '          origin       | %s' % (origin) + end_color)
            print(line_color + '          more info    | %s' % (moreInfo) + end_color)
            print(line_color + '          threshold    | %s' % (thresholdInfo) + end_color)
            print(line_color + '          correlate    | %s' % (','.join(correlatedEvents)) + end_color)

        if 'tags' in options.show and tags:
            for t in tags:
                print(line_color + '            tag | %s' % (t) + end_color)

        if 'history' in options.show:
            for hist in alert['history']:
                if 'event' in hist:
                    alertid     = hist['id']
                    createTime  = datetime.datetime.strptime(hist['createTime'], '%Y-%m-%dT%H:%M:%S.%fZ')
                    createTime  = createTime.replace(tzinfo=pytz.utc)
                    event       = hist['event']
                    receiveTime = datetime.datetime.strptime(hist['receiveTime'], '%Y-%m-%dT%H:%M:%S.%fZ')
                    receiveTime = receiveTime.replace(tzinfo=pytz.utc)
                    severity    = hist['severity']
                    value       = hist['value']
                    text        = hist['text']
                    print(line_color + '  %s|%s|%s|%-18s|%12s|%16s|%12s' % (alertid[0:8],
                        receiveTime.astimezone(tz).strftime(DATE_FORMAT),
                        SEV[severity],
                        resource.split('.')[-1],
                        group,
                        event,
                        value) + end_color)
                    print(line_color + '    |%s' % (text) + end_color)
                if 'status' in hist:
                    updateTime  = datetime.datetime.strptime(hist['updateTime'], '%Y-%m-%dT%H:%M:%S.%fZ')
                    updateTime  = updateTime.replace(tzinfo=pytz.utc)
                    status      = hist['status']
                    print(line_color + '    %s|%s' % (updateTime.astimezone(tz).strftime(DATE_FORMAT), status) + end_color)

    if 'counts' in options.show:
        print
        print('Crit|Majr|Minr|Warn|Norm|Info|Dbug')
        print(
            COLOR['CRITICAL'] + '%4d' % response['alerts']['severityCounts']['critical'] + ENDC + ' ' +
            COLOR['MAJOR']    + '%4d' % response['alerts']['severityCounts']['major']    + ENDC + ' ' +
            COLOR['MINOR']    + '%4d' % response['alerts']['severityCounts']['minor']    + ENDC + ' ' +
            COLOR['WARNING']  + '%4d' % response['alerts']['severityCounts']['warning']  + ENDC + ' ' +
            COLOR['NORMAL']   + '%4d' % response['alerts']['severityCounts']['normal']   + ENDC + ' ' +
            COLOR['INFORM']   + '%4d' % response['alerts']['severityCounts']['inform']   + ENDC + ' ' +
            COLOR['DEBUG']    + '%4d' % response['alerts']['severityCounts']['debug']    + ENDC)

    if not options.nofooter:
        now = datetime.datetime.utcnow()
        now = now.replace(tzinfo=pytz.utc)
        print
        print "Total: %d (produced on %s at %s by %s,v%s on %s in %sms)" % (count, now.astimezone(tz).strftime("%d/%m/%y"), now.astimezone(tz).strftime("%H:%M:%S %Z"), PGM, __version__, os.uname()[1], int((end - start) * 1000))

if __name__ == '__main__':
    main()

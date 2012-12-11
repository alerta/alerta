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
import urllib2, urllib
import operator
import pytz

__version__ = '1.3.3'

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
                      action="append",
                      dest="alertid",
                      help="Alert ID (can use 8-char abbrev id)")
    parser.add_option("-E",
                      "--environment",
                      action="append",
                      dest="environment",
                      help="Environment eg. PROD, REL, QA, TEST, CODE, STAGE, DEV, LWP, INFRA")
    parser.add_option( "--not-environment",
                      action="append",
                      dest="not_environment")
    parser.add_option("-S",
                      "--svc",
                      "--service",
                      action="append",
                      dest="service",
                      help="Service eg. R1, R2, Discussion, Soulmates, ContentAPI, MicroApp, FlexibleContent, Mutualisation, SharedSvcs")
    parser.add_option( "--not-service",
                      action="append",
                      dest="not_service")
    parser.add_option("-r",
                      "--resource",
                      action="append",
                      dest="resource",
                      help="Resource under alarm eg. hostname, network device, application")
    parser.add_option("--not-resource",
                      action="append",
                      dest="not_resource")
    parser.add_option("-s",
                      "--severity",
                      action="append",
                      dest="severity",
                      help="Severity eg. CRITICAL, MAJOR, MINOR, WARNING, NORMAL, INFORM, DEBUG")
    parser.add_option("--not-severity",
                      action="append",
                      dest="not_severity")
    parser.add_option( "--status",
                      action="append",
                      dest="status",
                      help="Status eg. OPEN, ACK, CLOSED, EXPIRED")
    parser.add_option( "--not-status",
                      action="append",
                      dest="not_status")
    parser.add_option("-e",
                      "--event",
                      action="append",
                      dest="event",
                      help="Event name eg. HostAvail, PingResponse, AppStatus")
    parser.add_option("--not-event",
                      action="append",
                      dest="not_event")
    parser.add_option("-g",
                      "--group",
                      action="append",
                      dest="group",
                      help="Event group eg. Application, Backup, Database, HA, Hardware, Job, Network, OS, Performance, Security")
    parser.add_option("--not-group",
                      action="append",
                      dest="not_group")
    parser.add_option("--origin",
                      action="append",
                      dest="origin",
                      help="Origin of the alert eg. alert-sender, alert-ganglia")
    parser.add_option("--not-origin",
                      action="append",
                      dest="not_origin")
    parser.add_option("-v",
                      "--value",
                      action="append",
                      dest="value",
                      help="Event value eg. 100%, Down, PingFail, 55tps, ORA-1664")
    parser.add_option("--not-value",
                      action="append",
                      dest="not_value")
    parser.add_option("-T",
                      "--tags",
                      action="append",
                      dest="tags")
    parser.add_option( "--not-tags",
                      action="append",
                      dest="not_tags")
    parser.add_option("-t",
                      "--text",
                      action="append",
                      dest="text")
    parser.add_option("--not-text",
                      action="append",
                      dest="not_text")
    parser.add_option("--show",
                      action="append",
                      dest="show",
                      default=[],
                      help="Show 'text', 'summary', 'times', 'attributes', 'details', 'tags', 'history', 'counts' and 'color'")
    parser.add_option("-o",
                      "--orderby",
                      "--sortby",
                      "--sort-by",
                      dest="sortby",
                      default='lastReceiveTime',
                      help="Sort by attribute (default: createTime)")
    parser.add_option("-w",
                      "--watch",
                      action="store_true",
                      dest="watch",
                      default=False,
                      help="Periodically poll for new  alerts every 2 seconds.")
    parser.add_option("-n",
                      "--interval",
                      type=int,
                      dest="interval",
                      default=2,
                      help="Change the default watch interval.")
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

    query = dict()

    if options.minutes or options.hours or options.days:
        now = datetime.datetime.utcnow()
        fromTime = now - datetime.timedelta(days=options.days, minutes=options.minutes+options.hours*60)
        query['from-date'] = fromTime.replace(microsecond=0).isoformat() + ".%03dZ" % (fromTime.microsecond//1000)
        now = now.replace(tzinfo=pytz.utc)
        fromTime = fromTime.replace(tzinfo=pytz.utc)
    elif options.watch:
        fromTime = datetime.datetime.utcnow()
        query['from-date'] = fromTime.replace(microsecond=0).isoformat() + ".%03dZ" % (fromTime.microsecond//1000)

    if options.alertid:
        query['id'] = '|'.join(options.alertid)

    if options.environment:
        query['environment'] = '|'.join(options.environment)

    if options.not_environment:
        query['-environment'] = '|'.join(options.not_environment)

    if options.service:
        query['service'] = '|'.join(options.service)

    if options.not_service:
        query['-service'] = '|'.join(options.not_service)

    if options.resource:
        query['resource'] = '|'.join(options.resource)

    if options.not_resource:
        query['-resource'] = '|'.join(options.not_resource)

    if options.severity:
        query['severity'] = '|'.join(options.severity).upper()

    if options.not_severity:
        query['-severity'] = '|'.join(options.not_severity).upper()

    if not options.status:
        query['status'] = 'OPEN|ACK|CLOSED'

    if options.status:
        query['status'] = '|'.join(options.status).upper()

    if options.not_status:
        query['-status'] = '|'.join(options.not_status).upper()

    if options.event:
        query['event'] = '|'.join(options.event)

    if options.not_event:
        query['-event'] = '|'.join(options.not_event)

    if options.group:
        query['group'] = '|'.join(options.group)

    if options.not_group:
        query['-group'] = '|'.join(options.not_group)

    if options.value:
        query['value'] = '|'.join(options.value)

    if options.not_value:
        query['-value'] = '|'.join(options.not_value)

    if options.origin:
        query['origin'] = '|'.join(options.origin)

    if options.not_origin:
        query['-origin'] = '|'.join(options.not_origin)

    if options.tags:
        query['tags'] = '|'.join(options.tags)

    if options.not_tags:
        query['-tags'] = '|'.join(options.not_tags)

    if options.text:
        query['text'] = '|'.join(options.text)

    if options.not_text:
        query['-text'] = '|'.join(options.not_text)

    if options.sortby:
        query['sort-by'] = options.sortby

    if options.limit:
        query['limit'] = options.limit

    if options.show == ['counts']:
        query['hide-alert-details'] = 'true'

    url = "%s?%s" % (API_URL, urllib.urlencode(query))

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
            print "        show: %s" % ','.join(options.show)
        if options.sortby:
            print "     sort by: %s" % options.sortby
        if options.alertid:
            print "    alert id: ^%s" % ','.join(options.alertid)
        if options.environment:
            print " environment: %s" % ','.join(options.environment)
        if options.service:
            print "     service: %s" % ','.join(options.service)
        if options.resource:
            print "    resource: %s" % ','.join(options.resource)
        if options.origin:
            print "      origin: %s" % ','.join(options.origin)
        if options.severity:
            print "    severity: %s" % ','.join(options.severity)
        if options.status:
            print "      status: %s" % ','.join(options.status)
        if options.event:
            print "       event: %s" % ','.join(options.event)
        if options.group:
            print "       group: %s" % ','.join(options.group)
        if options.value:
            print "       value: %s" % ','.join(options.value)
        if options.text:
            print "        text: %s" % ','.join(options.text)
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
    while True:

        start = time.time()
        try:
            output = urllib2.urlopen(url)
            fromTime = datetime.datetime.utcnow()
            response = json.loads(output.read())['response']
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
                    ','.join(environment),
                    ','.join(service),
                    resource,
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
                print(line_color + '          environment  | %s' % (','.join(environment)) + end_color)
                print(line_color + '          service      | %s' % (','.join(service)) + end_color)
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
                            resource,
                            group,
                            event,
                            value) + end_color)
                        print(line_color + '    |%s' % (text) + end_color)
                    if 'status' in hist:
                        updateTime  = datetime.datetime.strptime(hist['updateTime'], '%Y-%m-%dT%H:%M:%S.%fZ')
                        updateTime  = updateTime.replace(tzinfo=pytz.utc)
                        status      = hist['status']
                        print(line_color + '    %s|%s' % (updateTime.astimezone(tz).strftime(DATE_FORMAT), status) + end_color)

        if options.watch:
            time.sleep(options.interval)
            query['from-date'] = fromTime.replace(microsecond=0).isoformat() + ".%03dZ" % (fromTime.microsecond//1000)
            url = "%s?%s" % (API_URL, urllib.urlencode(query))
        else:
            break

    if 'counts' in options.show:
        print
        print('OPEN|ACK|CLOSED' + '  '),
        print('Crit|Majr|Minr|Warn|Norm|Info|Dbug')
        print(
            '%4d' % response['alerts']['statusCounts']['open'] + ' ' +
            '%3d' % response['alerts']['statusCounts']['ack'] + ' ' +
            '%6d' % response['alerts']['statusCounts']['closed'] + '  '),
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
    try:
        main()
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)

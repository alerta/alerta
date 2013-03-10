import os
import sys
import urllib
import urllib2
import json
import time

import datetime

import pytz

from alerta.common import log as logging
from alerta.common import config
from alerta.alert import severity, status

Version = '2.0.0'

LOG = logging.getLogger(__name__)
CONF = config.CONF

_DEFAULT_CONSOLE_DATE_FORMAT = '%d/%m/%y %H:%M:%S'

DEFAULT_TIMEOUT = 3600

class QueryClient(object):

    def main(self):

        API_URL = 'http://%s:%s%s/alerts' % (CONF.api_host, CONF.api_port,
                                             CONF.api_endpoint if CONF.api_endpoint != '/' else '')
        query = dict()

        if CONF.minutes or CONF.hours or CONF.days:
            now = datetime.datetime.utcnow()
            from_time = now - datetime.timedelta(days=CONF.days, minutes=CONF.minutes + CONF.hours * 60)
            query['from-date'] = from_time.replace(microsecond=0).isoformat() + ".%03dZ" % (from_time.microsecond // 1000)
            now = now.replace(tzinfo=pytz.utc)
            from_time = from_time.replace(tzinfo=pytz.utc)
        elif CONF.watch:
            from_time = datetime.datetime.utcnow()
            query['from-date'] = from_time.replace(microsecond=0).isoformat() + ".%03dZ" % (from_time.microsecond // 1000)

        if CONF.alertid:
            query['id'] = '|'.join(CONF.alertid)

        if CONF.environment:
            query['environment'] = '|'.join(CONF.environment)

        if CONF.not_environment:
            query['-environment'] = '|'.join(CONF.not_environment)

        if CONF.service:
            query['service'] = '|'.join(CONF.service)

        if CONF.not_service:
            query['-service'] = '|'.join(CONF.not_service)

        if CONF.resource:
            query['resource'] = '|'.join(CONF.resource)

        if CONF.not_resource:
            query['-resource'] = '|'.join(CONF.not_resource)

        if CONF.severity:
            query['severity'] = '|'.join(CONF.severity)

        if CONF.not_severity:
            query['-severity'] = '|'.join(CONF.not_severity)

        if not CONF.status:
            query['status'] = 'OPEN|ACK|CLOSED'

        if CONF.status:
            query['status'] = '|'.join(CONF.status)

        if CONF.not_status:
            query['-status'] = '|'.join(CONF.not_status)

        if CONF.event:
            query['event'] = '|'.join(CONF.event)

        if CONF.not_event:
            query['-event'] = '|'.join(CONF.not_event)

        if CONF.group:
            query['group'] = '|'.join(CONF.group)

        if CONF.not_group:
            query['-group'] = '|'.join(CONF.not_group)

        if CONF.value:
            query['value'] = '|'.join(CONF.value)

        if CONF.not_value:
            query['-value'] = '|'.join(CONF.not_value)

        if CONF.origin:
            query['origin'] = '|'.join(CONF.origin)

        if CONF.not_origin:
            query['-origin'] = '|'.join(CONF.not_origin)

        if CONF.tags:
            query['tags'] = '|'.join(CONF.tags)

        if CONF.not_tags:
            query['-tags'] = '|'.join(CONF.not_tags)

        if CONF.text:
            query['text'] = '|'.join(CONF.text)

        if CONF.not_text:
            query['-text'] = '|'.join(CONF.not_text)

        if CONF.sortby:
            query['sort-by'] = CONF.sortby

        if CONF.limit:
            query['limit'] = CONF.limit

        if CONF.show == ['counts']:
            query['hide-alert-details'] = 'true'

        url = "%s?%s" % (API_URL, urllib.urlencode(query))

        if CONF.dry_run:
            print "DEBUG: %s" % (url)
            sys.exit(0)

        tz = pytz.timezone(CONF.timezone)

        if not CONF.noheader:
            print "Alerta Report Tool"
            print "  api server: %s:%s" % (CONF.api_host, CONF.api_port)
            print "    timezone: %s" % CONF.timezone
            if CONF.minutes or CONF.hours or CONF.days:
                print "    interval: %s - %s" % (
                    from_time.astimezone(tz).strftime(_DEFAULT_CONSOLE_DATE_FORMAT),
                    now.astimezone(tz).strftime(_DEFAULT_CONSOLE_DATE_FORMAT))
            if CONF.show:
                print "        show: %s" % ','.join(CONF.show)
            if CONF.sortby:
                print "     sort by: %s" % CONF.sortby
            if CONF.alertid:
                print "    alert id: ^%s" % ','.join(CONF.alertid)
            if CONF.environment:
                print " environment: %s" % ','.join(CONF.environment)
            if CONF.not_environment:
                print " environment: (not) %s" % ','.join(CONF.not_environment)
            if CONF.service:
                print "     service: %s" % ','.join(CONF.service)
            if CONF.not_service:
                print "     service: (not) %s" % ','.join(CONF.not_service)
            if CONF.resource:
                print "    resource: %s" % ','.join(CONF.resource)
            if CONF.not_resource:
                print "    resource: (not) %s" % ','.join(CONF.not_resource)
            if CONF.origin:
                print "      origin: %s" % ','.join(CONF.origin)
            if CONF.not_origin:
                print "      origin: (not) %s" % ','.join(CONF.not_origin)
            if CONF.severity:
                print "    severity: %s" % ','.join(CONF.severity)
            if CONF.not_severity:
                print "    severity: (not) %s" % ','.join(CONF.not_severity)
            if CONF.status:
                print "      status: %s" % ','.join(CONF.status)
            if CONF.not_status:
                print "      status: (not) %s" % ','.join(CONF.not_status)
            if CONF.event:
                print "       event: %s" % ','.join(CONF.event)
            if CONF.not_event:
                print "       event: (not) %s" % ','.join(CONF.not_event)
            if CONF.group:
                print "       group: %s" % ','.join(CONF.group)
            if CONF.not_group:
                print "       group: (not) %s" % ','.join(CONF.not_group)
            if CONF.value:
                print "       value: %s" % ','.join(CONF.value)
            if CONF.not_value:
                print "       value: (not) %s" % ','.join(CONF.not_value)
            if CONF.text:
                print "        text: %s" % ','.join(CONF.text)
            if CONF.not_text:
                print "        text: (not) %s" % ','.join(CONF.not_text)
            if CONF.tags:
                print "        tags: %s" % ','.join(CONF.tags)
            if CONF.not_tags:
                print "        tags: (not) %s" % ','.join(CONF.not_tags)
            if CONF.limit:
                print "       count: %d" % CONF.limit
            print

        if 'some' in CONF.show:
            CONF.show.append('text')
            CONF.show.append('details')
        elif 'all' in CONF.show:
            CONF.show.append('text')
            CONF.show.append('attributes')
            CONF.show.append('times')
            CONF.show.append('details')
            CONF.show.append('tags')

        line_color = ''
        end_color = ''
        if 'color' in CONF.show or CONF.color:
            end_color = severity.ENDC

        # Query API for alerts
        while True:

            start = time.time()
            try:
                output = urllib2.urlopen(url)
                from_time = datetime.datetime.utcnow()
                response = json.loads(output.read())['response']
            except urllib2.URLError, e:
                print "ERROR: Alert query %s failed - %s" % (url, e)
                sys.exit(1)
            except (KeyboardInterrupt, SystemExit):
                sys.exit(0)
            end = time.time()

            if CONF.sortby in ['createTime', 'receiveTime', 'lastReceiveTime']:
                alertDetails = reversed(response['alerts']['alertDetails'])
            else:
                alertDetails = response['alerts']['alertDetails']

            count = 0
            for alert in alertDetails:
                resource = alert.get('resource', None)
                event = alert.get('event', None)
                correlate = alert.get('correlatedEvents', None)
                group = alert.get('group', None)
                value = alert.get('value', None)
                current_status = status.parse_status(alert.get('status', None))
                current_severity = severity.parse_severity(alert.get('severity', None))
                previous_severity = severity.parse_severity(alert.get('previousSeverity', None))
                environment = alert.get('environment', None)
                service = alert.get('service', None)
                text = alert.get('text', None)
                event_type = alert.get('type', None)
                tags = alert.get('tags', None)
                origin = alert.get('origin', None)
                repeat = alert.get('repeat', None)
                duplicate_count = int(alert.get('duplicateCount', 0))
                threshold_info = alert.get('thresholdInfo', None)
                summary = alert.get('summary', None)
                timeout = alert.get('timeout', 0)
                alertid = alert.get('id', None)
                last_receive_id = alert.get('lastReceiveId', None)
                create_time = datetime.datetime.strptime(alert.get('createTime', None), '%Y-%m-%dT%H:%M:%S.%fZ')
                create_time = create_time.replace(tzinfo=pytz.utc)
                receive_time = datetime.datetime.strptime(alert.get('receiveTime', None), '%Y-%m-%dT%H:%M:%S.%fZ')
                receive_time = receive_time.replace(tzinfo=pytz.utc)
                last_receive_time = datetime.datetime.strptime(alert.get('lastReceiveTime', None), '%Y-%m-%dT%H:%M:%S.%fZ')
                last_receive_time = last_receive_time.replace(tzinfo=pytz.utc)
                trend_indication = alert.get('trendIndication', None)
                expire_time = datetime.datetime.strptime(alert.get('expireTime', None), '%Y-%m-%dT%H:%M:%S.%fZ')
                expire_time = expire_time.replace(tzinfo=pytz.utc)

                # TODO(nsatterl): add these to Alert class
                graphs = alert.get('graphs', ['n/a'])
                more_info = alert.get('moreInfo', 'n/a')
                repeat = alert.get('repeat', False)

                delta = receive_time - create_time
                latency = int(delta.days * 24 * 60 * 60 * 1000 + delta.seconds * 1000 + delta.microseconds / 1000)

                count += 1

                if CONF.sortby == 'createTime':
                    displayTime = create_time
                elif CONF.sortby == 'receiveTime':
                    displayTime = receive_time
                else:
                    displayTime = last_receive_time

                if 'color' in CONF.show or CONF.color:
                    line_color = severity._COLOR_MAP[current_severity]

                if 'summary' in CONF.show:
                    print(line_color + '%s' % summary + end_color)
                else:
                    print(line_color + '%s|%s|%s|%5d|%-5s|%-10s|%-18s|%12s|%16s|%12s' % (
                        alertid[0:8],
                        displayTime.astimezone(tz).strftime(_DEFAULT_CONSOLE_DATE_FORMAT),
                        severity._ABBREV_SEVERITY_MAP[current_severity],
                        duplicate_count,
                        ','.join(environment),
                        ','.join(service),
                        resource,
                        group,
                        event,
                        value) + end_color)

                if 'text' in CONF.show:
                    print(line_color + '   |%s' % (text) + end_color)

                if 'attributes' in CONF.show:
                    print(
                        line_color + '    severity | %s (%s) -> %s (%s)' % (
                            previous_severity.capitalize(), severity.name_to_code(previous_severity),
                            current_severity.capitalize(), severity.name_to_code(current_severity)) + end_color)
                    print(line_color + '    trend    | %s' % trend_indication + end_color)
                    print(line_color + '    status   | %s' % current_status.capitalize() + end_color)
                    print(line_color + '    resource | %s' % resource + end_color)
                    print(line_color + '    group    | %s' % group + end_color)
                    print(line_color + '    event    | %s' % event + end_color)
                    print(line_color + '    value    | %s' % value + end_color)

                if 'times' in CONF.show:
                    print(
                        line_color + '      time created  | %s' % (
                        create_time.astimezone(tz).strftime(_DEFAULT_CONSOLE_DATE_FORMAT)) + end_color)
                    print(line_color + '      time received | %s' % (
                        receive_time.astimezone(tz).strftime(_DEFAULT_CONSOLE_DATE_FORMAT)) + end_color)
                    print(line_color + '      last received | %s' % (
                        last_receive_time.astimezone(tz).strftime(_DEFAULT_CONSOLE_DATE_FORMAT)) + end_color)
                    print(line_color + '      latency       | %sms' % latency + end_color)
                    print(line_color + '      timeout       | %ss' % timeout + end_color)
                    if expire_time:
                        print(line_color + '      expire time   | %s' % (
                            expire_time.astimezone(tz).strftime(_DEFAULT_CONSOLE_DATE_FORMAT)) + end_color)

                if 'details' in CONF.show:
                    print(line_color + '          alert id     | %s' % alertid + end_color)
                    print(line_color + '          last recv id | %s' % last_receive_id + end_color)
                    print(line_color + '          environment  | %s' % (','.join(environment)) + end_color)
                    print(line_color + '          service      | %s' % (','.join(service)) + end_color)
                    print(line_color + '          resource     | %s' % resource + end_color)
                    print(line_color + '          type         | %s' % event_type + end_color)
                    print(line_color + '          origin       | %s' % origin + end_color)
                    print(line_color + '          more info    | %s' % more_info + end_color)
                    print(line_color + '          threshold    | %s' % threshold_info + end_color)
                    print(line_color + '          correlate    | %s' % (','.join(correlate)) + end_color)

                if 'tags' in CONF.show and tags:
                    for t in tags:
                        print(line_color + '            tag | %s' % (t) + end_color)

                if 'history' in CONF.show:
                    for hist in alert['history']:
                        if 'event' in hist:
                            alertid = hist['id']
                            create_time = datetime.datetime.strptime(hist['createTime'], '%Y-%m-%dT%H:%M:%S.%fZ')
                            create_time = create_time.replace(tzinfo=pytz.utc)
                            event = hist['event']
                            receive_time = datetime.datetime.strptime(hist['receiveTime'], '%Y-%m-%dT%H:%M:%S.%fZ')
                            receive_time = receive_time.replace(tzinfo=pytz.utc)
                            historical_severity = hist['severity']
                            value = hist['value']
                            text = hist['text']
                            print(line_color + '  %s|%s|%s|%-18s|%12s|%16s|%12s' % (alertid[0:8],
                                                                                    receive_time.astimezone(tz).strftime(
                                                                                        _DEFAULT_CONSOLE_DATE_FORMAT),
                                                                                    severity._ABBREV_SEVERITY_MAP[historical_severity],
                                                                                    resource,
                                                                                    group,
                                                                                    event,
                                                                                    value) + end_color)
                            print(line_color + '    |%s' % (text) + end_color)
                        if 'status' in hist:
                            update_time = datetime.datetime.strptime(hist['updateTime'], '%Y-%m-%dT%H:%M:%S.%fZ')
                            update_time = update_time.replace(tzinfo=pytz.utc)
                            historical_status = hist['status']
                            print(line_color + '    %s|%s' % (
                                update_time.astimezone(tz).strftime(_DEFAULT_CONSOLE_DATE_FORMAT), historical_status) + end_color)

            if CONF.watch:
                try:
                    time.sleep(CONF.interval)
                except (KeyboardInterrupt, SystemExit):
                    sys.exit(0)
                query['from-date'] = response['alerts']['lastTime']
                url = "%s?%s" % (API_URL, urllib.urlencode(query))
            else:
                break

        if 'counts' in CONF.show:
            print
            print('%s|%s|%s' + '  ' % (status.OPEN, status.ACK, status.CLOSED)),
            print('Crit|Majr|Minr|Warn|Norm|Info|Dbug')
            print(
                '%4d' % response['alerts']['statusCounts']['open'] + ' ' +
                '%3d' % response['alerts']['statusCounts']['ack'] + ' ' +
                '%6d' % response['alerts']['statusCounts']['closed'] + '  '),
            print(
                severity._COLOR_MAP[severity.CRITICAL] + '%4d' % response['alerts']['severityCounts']['critical'] + severity.ENDC + ' ' +
                severity._COLOR_MAP[severity.MAJOR] + '%4d' % response['alerts']['severityCounts']['major'] + severity.ENDC + ' ' +
                severity._COLOR_MAP[severity.MINOR] + '%4d' % response['alerts']['severityCounts']['minor'] + severity.ENDC + ' ' +
                severity._COLOR_MAP[severity.WARNING] + '%4d' % response['alerts']['severityCounts']['warning'] + severity.ENDC + ' ' +
                severity._COLOR_MAP[severity.NORMAL] + '%4d' % response['alerts']['severityCounts']['normal'] + severity.ENDC + ' ' +
                severity._COLOR_MAP[severity.INFORM] + '%4d' % response['alerts']['severityCounts']['inform'] + severity.ENDC + ' ' +
                severity._COLOR_MAP[severity.DEBUG] + '%4d' % response['alerts']['severityCounts']['debug'] + severity.ENDC)

        if not CONF.nofooter:
            now = datetime.datetime.utcnow()
            now = now.replace(tzinfo=pytz.utc)
            if response['more']:
                has_more = '+'
            else:
                has_more = ''
            print
            print "Total: %d%s (produced on %s at %s by %s,v%s on %s in %sms)" % (
                count, has_more, now.astimezone(tz).strftime("%d/%m/%y"), now.astimezone(tz).strftime("%H:%M:%S %Z"), sys.argv[0],
                Version, os.uname()[1], int((end - start) * 1000))


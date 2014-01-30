import os
import sys
import json
import time
import datetime
import prettytable
import pytz

from email import utils

from alerta.common import log as logging
from alerta.common.api import ApiClient
from alerta.common import status_code, severity_code
from alerta.common import config
from alerta.common.utils import relative_date
from alerta.common.graphite import StatsD

Version = '2.0.22'

LOG = logging.getLogger(__name__)
CONF = config.CONF


class QueryClient(object):

    def main(self):

        api = ApiClient()
        query = dict()

        self.now = datetime.datetime.utcnow()
        from_time = self.now

        if CONF.minutes or CONF.hours or CONF.days:
            from_time = self.now - datetime.timedelta(days=CONF.days, minutes=CONF.minutes + CONF.hours * 60)
            query['from-date'] = from_time.replace(microsecond=0).isoformat() + ".%03dZ" % (from_time.microsecond // 1000)
        elif CONF.watch:
            query['from-date'] = from_time.replace(microsecond=0).isoformat() + ".%03dZ" % (from_time.microsecond // 1000)

        self.now = self.now.replace(tzinfo=pytz.utc)
        from_time = from_time.replace(tzinfo=pytz.utc)

        if CONF.alertid:
            query['id'] = CONF.alertid

        if CONF.environment:
            query['environment'] = CONF.environment

        if CONF.not_environment:
            query['environment!'] = CONF.not_environment

        if CONF.service:
            query['service'] = CONF.service

        if CONF.not_service:
            query['service!'] = CONF.not_service

        if CONF.resource:
            query['resource'] = CONF.resource

        if CONF.not_resource:
            query['resource!'] = CONF.not_resource

        if CONF.severity:
            query['severity'] = CONF.severity

        if CONF.not_severity:
            query['severity!'] = CONF.not_severity

        if not CONF.status:
            query['status'] = '~%s|%s|%s' % (status_code.OPEN, status_code.ACK, status_code.CLOSED)

        if CONF.status:
            query['status'] = CONF.status

        if CONF.not_status:
            query['status!'] = CONF.not_status

        if CONF.event:
            query['event'] = CONF.event

        if CONF.not_event:
            query['event'] = CONF.not_event

        if CONF.group:
            query['group'] = CONF.group

        if CONF.not_group:
            query['group!'] = CONF.not_group

        if CONF.value:
            query['value'] = CONF.value

        if CONF.not_value:
            query['value!'] = CONF.not_value

        if CONF.origin:
            query['origin'] = CONF.origin

        if CONF.not_origin:
            query['origin!'] = CONF.not_origin

        if CONF.tags:
            query['tags'] = CONF.tags

        if CONF.not_tags:
            query['tags!'] = CONF.not_tags

        if CONF.text:
            query['text'] = CONF.text

        if CONF.not_text:
            query['text!'] = CONF.not_text

        if CONF.event_type:
            query['type'] = CONF.event_type

        if CONF.not_event_type:
            query['type!'] = CONF.not_event_type

        if CONF.repeat:
            query['repeat'] = CONF.repeat

        if CONF.sortby:
            query['sort-by'] = CONF.sortby

        if CONF.limit:
            query['limit'] = CONF.limit

        if CONF.show == ['counts']:
            query['hide-alert-details'] = 'true'

        if CONF.oneline:
            CONF.format = '{i} {rd} {sa} {E} {S} {r} {g} {e} {v} {t}'

        if CONF.query:
            query['q'] = CONF.query

        if CONF.json:
            CONF.output = 'json'

        self.tz = pytz.timezone(CONF.timezone)

        if CONF.output == 'table':
            pt = prettytable.PrettyTable(["Alert ID", "Last Receive Time", "Severity", "Dupl.", "Environment", "Service", "Resource", "Group", "Event", "Value"])
            col_text = []
        elif not CONF.noheader:
            print "Alerta Report Tool"
            print "  api server: %s:%s" % (CONF.api_host, CONF.api_port)
            print "    timezone: %s" % CONF.timezone
            if CONF.minutes or CONF.hours or CONF.days:
                print "    interval: %s - %s" % (
                    self._format_date(from_time),
                    self._format_date(self.now))
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
            if CONF.event_type:
                print "  event type: %s" % ','.join(CONF.event_type)
            if CONF.not_event_type:
                print "  event type: (not) %s" % ','.join(CONF.not_event_type)
            if CONF.repeat:
                print "     repeats: %s" % CONF.repeat
            if CONF.limit:
                print "       count: %d" % CONF.limit
            if CONF.query:
                print "       query: %s" % CONF.query
            if CONF.delete:
                print "      action: DELETE"
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
        if 'color' in CONF.show or CONF.color or os.environ.get('CLICOLOR', None):
            end_color = severity_code.ENDC

        # Query API for alerts
        while True:

            start = time.time()
            try:
                response = api.query(query)
            except (KeyboardInterrupt, SystemExit):
                sys.exit(0)
            end = time.time()

            if response['status'] == 'error':
                print "ERROR: %s" % (response['message'])
                LOG.error('%s', response['message'])
                sys.exit(1)

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
                current_status = status_code.parse_status(alert.get('status', None))
                current_severity = severity_code.parse_severity(alert.get('severity', None))
                previous_severity = severity_code.parse_severity(alert.get('previousSeverity', None))
                environment = alert.get('environment', None)
                service = alert.get('service', None)
                text = alert.get('text', None)
                event_type = alert.get('type', None)
                tags = alert.get('tags', None)
                origin = alert.get('origin', None)
                repeat = alert.get('repeat', False)
                duplicate_count = int(alert.get('duplicateCount', 0))
                threshold_info = alert.get('thresholdInfo', None)
                summary = alert.get('summary', None)
                timeout = alert.get('timeout', 0)
                alertid = alert.get('id', None)
                raw_data = alert.get('rawData', None)

                last_receive_id = alert.get('lastReceiveId', None)

                create_time = datetime.datetime.strptime(alert.get('createTime', None), '%Y-%m-%dT%H:%M:%S.%fZ')
                create_time = create_time.replace(tzinfo=pytz.utc)
                create_time_epoch = time.mktime(create_time.timetuple())

                receive_time = datetime.datetime.strptime(alert.get('receiveTime', None), '%Y-%m-%dT%H:%M:%S.%fZ')
                receive_time = receive_time.replace(tzinfo=pytz.utc)
                receive_time_epoch = time.mktime(receive_time.timetuple())

                last_receive_time = datetime.datetime.strptime(alert.get('lastReceiveTime', None), '%Y-%m-%dT%H:%M:%S.%fZ')
                last_receive_time = last_receive_time.replace(tzinfo=pytz.utc)
                last_receive_time_epoch = time.mktime(last_receive_time.timetuple())

                expire_time = datetime.datetime.strptime(alert.get('expireTime', None), '%Y-%m-%dT%H:%M:%S.%fZ')
                expire_time = expire_time.replace(tzinfo=pytz.utc)
                expire_time_epoch = time.mktime(expire_time.timetuple())

                trend_indication = alert.get('trendIndication', None)
                more_info = alert.get('moreInfo', 'n/a')
                graph_urls = alert.get('graphUrls', ['n/a'])

                delta = receive_time - create_time
                latency = int(delta.days * 24 * 60 * 60 * 1000 + delta.seconds * 1000 + delta.microseconds / 1000)

                format_kwargs = {
                    'I': alertid,
                    'i': alertid[0:8],
                    'r': resource,
                    'e': event,
                    'C': ','.join(correlate),
                    'g': group,
                    'v': value,
                    'st': current_status.capitalize(),
                    's': current_severity.capitalize(),
                    'sa': severity_code._ABBREV_SEVERITY_MAP.get(current_severity, '****'),
                    'sc': severity_code.name_to_code(current_severity),
                    'sP': previous_severity.capitalize(),
                    'sPa': severity_code._ABBREV_SEVERITY_MAP.get(previous_severity, '****'),
                    'sPc': severity_code.name_to_code(previous_severity),
                    'E': ','.join(environment),
                    'S': ','.join(service),
                    't': text.encode('utf-8'),
                    'eT': event_type,
                    'T': ','.join(tags),
                    'O': origin,
                    'R': repeat,
                    'D': duplicate_count,
                    'th': threshold_info,
                    'y': summary,
                    'o': timeout,
                    'B': raw_data,
                    'ti': trend_indication,
                    'm': more_info,
                    'u': ','.join(graph_urls),
                    'L': latency,
                    'lrI': last_receive_id,
                    'lri': last_receive_id[0:8],
                    'ci': create_time.replace(microsecond=0).isoformat() + ".%03dZ" % (create_time.microsecond // 1000),
                    'ct': create_time_epoch,
                    'cd': self._format_date(create_time),
                    'cD': utils.formatdate(create_time_epoch),
                    'ri': receive_time.replace(microsecond=0).isoformat() + ".%03dZ" % (receive_time.microsecond // 1000),
                    'rt': receive_time_epoch,
                    'rd': self._format_date(receive_time),
                    'rD': utils.formatdate(receive_time_epoch),
                    'li': last_receive_time.replace(microsecond=0).isoformat() + ".%03dZ" % (last_receive_time.microsecond // 1000),
                    'lt': last_receive_time_epoch,
                    'ld': self._format_date(last_receive_time),
                    'lD': utils.formatdate(last_receive_time_epoch),
                    'ei': expire_time.replace(microsecond=0).isoformat() + ".%03dZ" % (expire_time.microsecond // 1000),
                    'et': expire_time_epoch,
                    'ed': self._format_date(expire_time),
                    'eD': utils.formatdate(expire_time_epoch),
                    'n': '\n',
                }

                count += 1

                if CONF.delete:
                    try:
                        response = api.delete(alertid)
                    except (KeyboardInterrupt, SystemExit):
                        sys.exit(0)

                    print(line_color + 'DELETE %s %s' % (alertid, response['status']) + end_color)
                    continue

                if 'color' in CONF.show or CONF.color or os.environ.get('CLICOLOR', None):
                    line_color = severity_code._COLOR_MAP[current_severity]

                if CONF.output == 'json':
                    print(line_color + json.dumps(alert, indent=4) + end_color)
                    continue

                if CONF.sortby == 'createTime':
                    displayTime = create_time
                elif CONF.sortby == 'receiveTime':
                    displayTime = receive_time
                else:
                    displayTime = last_receive_time

                if CONF.output == 'table':
                    pt.add_row([
                        alertid,
                        self._format_date(displayTime),
                        severity_code._ABBREV_SEVERITY_MAP.get(current_severity, '****'),
                        duplicate_count,
                        ','.join(environment),
                        ','.join(service),
                        resource,
                        group,
                        event,
                        value]
                    )
                    if 'text' in CONF.show:
                        col_text.append(text)
                    continue

                if CONF.format:
                    try:
                        print line_color + CONF.format.format(**format_kwargs) + end_color
                    except (KeyError, IndexError), e:
                        print 'Format error: %s' % e
                        LOG.error('Format error: %s', e)
                    continue

                if 'summary' in CONF.show:
                    print(line_color + '%s' % summary + end_color)
                else:
                    print(line_color + '%s|%s|%s|%5d|%-5s|%-10s|%-18s|%12s|%16s|%12s' % (
                        alertid[0:8],
                        self._format_date(displayTime),
                        severity_code._ABBREV_SEVERITY_MAP.get(current_severity, '****'),
                        duplicate_count,
                        ','.join(environment),
                        ','.join(service),
                        resource,
                        group,
                        event,
                        value) + end_color)

                if 'text' in CONF.show:
                    print(line_color + '   |%s' % (text.encode('utf-8')) + end_color)

                if 'attributes' in CONF.show:
                    print(
                        line_color + '    severity | %s (%s) -> %s (%s)' % (
                            previous_severity.capitalize(), severity_code.name_to_code(previous_severity),
                            current_severity.capitalize(), severity_code.name_to_code(current_severity)) + end_color)
                    print(line_color + '    trend    | %s' % trend_indication + end_color)
                    print(line_color + '    status   | %s' % current_status.capitalize() + end_color)
                    print(line_color + '    resource | %s' % resource + end_color)
                    print(line_color + '    group    | %s' % group + end_color)
                    print(line_color + '    event    | %s' % event + end_color)
                    print(line_color + '    value    | %s' % value + end_color)

                if 'times' in CONF.show:
                    print(line_color + '      time created  | %s' % (
                        self._format_date(create_time)) + end_color)
                    print(line_color + '      time received | %s' % (
                        self._format_date(receive_time)) + end_color)
                    print(line_color + '      last received | %s' % (
                        self._format_date(last_receive_time)) + end_color)
                    print(line_color + '      latency       | %sms' % latency + end_color)
                    print(line_color + '      timeout       | %ss' % timeout + end_color)
                    if expire_time:
                        print(line_color + '      expire time   | %s' % (
                            self._format_date(expire_time)) + end_color)

                if 'details' in CONF.show:
                    print(line_color + '          alert id     | %s' % alertid + end_color)
                    print(line_color + '          last recv id | %s' % last_receive_id + end_color)
                    print(line_color + '          environment  | %s' % (','.join(environment)) + end_color)
                    print(line_color + '          service      | %s' % (','.join(service)) + end_color)
                    print(line_color + '          resource     | %s' % resource + end_color)
                    print(line_color + '          type         | %s' % event_type + end_color)
                    print(line_color + '          repeat       | %s' % repeat + end_color)
                    print(line_color + '          origin       | %s' % origin + end_color)
                    print(line_color + '          more info    | %s' % more_info + end_color)
                    print(line_color + '          threshold    | %s' % threshold_info + end_color)
                    print(line_color + '          correlate    | %s' % (','.join(correlate)) + end_color)
                    print(line_color + '          graphs       | %s' % (','.join(graph_urls)) + end_color)

                if 'tags' in CONF.show and tags:
                    for tag in tags.items():
                        print(line_color + '            tag %6s | %s' % tag + end_color)

                if 'raw' in CONF.show and raw_data:
                    print(line_color + '   | %s' % raw_data + end_color)

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
                                                                                    self._format_date(receive_time),
                                                                                    severity_code._ABBREV_SEVERITY_MAP[historical_severity],
                                                                                    resource,
                                                                                    group,
                                                                                    event,
                                                                                    value) + end_color)
                            print(line_color + '    |%s' % (text.encode('utf-8')) + end_color)
                        if 'status' in hist:
                            update_time = datetime.datetime.strptime(hist['updateTime'], '%Y-%m-%dT%H:%M:%S.%fZ')
                            update_time = update_time.replace(tzinfo=pytz.utc)
                            historical_status = hist['status']
                            print(line_color + '    %s|%s' % (
                                self._format_date(update_time), historical_status) + end_color)

            if CONF.watch:
                try:
                    time.sleep(CONF.interval)
                except (KeyboardInterrupt, SystemExit):
                    sys.exit(0)
                query['from-date'] = response['alerts']['lastTime']
            else:
                break

        if 'counts' in CONF.show:
            print
            print('%s|%s|%s' + '  ') % (status_code.OPEN, status_code.ACK, status_code.CLOSED),
            print('Crit|Majr|Minr|Warn|Norm|Info|Dbug')
            print(
                '%4d' % response['alerts']['statusCounts']['open'] + ' ' +
                '%3d' % response['alerts']['statusCounts']['ack'] + ' ' +
                '%6d' % response['alerts']['statusCounts']['closed'] + '  '),
            print(
                severity_code._COLOR_MAP[
                    severity_code.CRITICAL] + '%4d' % response['alerts']['severityCounts']['critical'] + severity_code.ENDC + ' ' +
                severity_code._COLOR_MAP[
                    severity_code.MAJOR] + '%4d' % response['alerts']['severityCounts']['major'] + severity_code.ENDC + ' ' +
                severity_code._COLOR_MAP[
                    severity_code.MINOR] + '%4d' % response['alerts']['severityCounts']['minor'] + severity_code.ENDC + ' ' +
                severity_code._COLOR_MAP[
                    severity_code.WARNING] + '%4d' % response['alerts']['severityCounts']['warning'] + severity_code.ENDC + ' ' +
                severity_code._COLOR_MAP[
                    severity_code.NORMAL] + '%4d' % response['alerts']['severityCounts']['normal'] + severity_code.ENDC + ' ' +
                severity_code._COLOR_MAP[
                    severity_code.INFORM] + '%4d' % response['alerts']['severityCounts']['informational'] + severity_code.ENDC + ' ' +
                severity_code._COLOR_MAP[
                    severity_code.DEBUG] + '%4d' % response['alerts']['severityCounts']['debug'] + severity_code.ENDC)

        response_time = int((end - start) * 1000)

        if CONF.output == 'table':
            if 'text' in CONF.show:
                pt.add_column("Text", col_text)
            print pt
        elif not CONF.nofooter:
            if 'more' in response and response['more']:
                has_more = '+'
            else:
                has_more = ''
            print
            print "Total: %d%s (produced on %s at %s by %s,v%s on %s in %sms)" % (
                count, has_more, self.now.astimezone(self.tz).strftime("%d/%m/%y"), self.now.astimezone(self.tz).strftime("%H:%M:%S %Z"),
                os.path.basename(sys.argv[0]), Version, os.uname()[1], response_time)

        statsd = StatsD()
        statsd.metric_send('alert.query.response_time.client', response_time, 'ms')

    def _format_date(self, event_time):

        if CONF.date == 'relative':
            event_time = event_time.replace(tzinfo=pytz.utc)
            event_time = event_time.astimezone(self.tz)
            return relative_date(event_time, self.now)
        elif CONF.date == 'local':
            return event_time.astimezone(self.tz).strftime('%Y/%m/%d %H:%M:%S')
        elif CONF.date == 'iso' or CONF.date == 'iso8601':
            return event_time.replace(microsecond=0).isoformat() + ".%03dZ" % (event_time.microsecond // 1000)
        elif CONF.date == 'rfc' or CONF.date == 'rfc2822':
            return utils.formatdate(time.mktime(event_time.timetuple()))
        elif CONF.date == 'short':
            return event_time.astimezone(self.tz).strftime('%a %d %H:%M:%S')
        elif CONF.date == 'epoch':
            return time.mktime(event_time.timetuple())
        elif CONF.date == 'raw':
            return event_time
        else:
            print "Unknown date format %s" % CONF.date
            sys.exit(1)

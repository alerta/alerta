#!/usr/bin/env python
########################################
#
# alerta-mgmt.py - Alerta Management
#
########################################

import os
import sys
try:
    import json
except ImportError:
    import simplejson as json
import time
import datetime
import pymongo
import urlparse
import logging
import re

__version__ = '1.1.0'

LOGFILE = '/var/log/alerta/alert-mgmt.log'

# Extend JSON Encoder to support ISO 8601 format dates
class DateEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.replace(microsecond=0).isoformat() + ".%03dZ" % (obj.microsecond//1000)
        else:
            return json.JSONEncoder.default(self, obj)

def main():

    start = time.time()

    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s alert-mgmt[%(process)d] %(levelname)s - %(message)s", filename=LOGFILE)
    logging.info('Received HTTP request %s %s' % (os.environ['REQUEST_METHOD'], os.environ['REQUEST_URI']))

    # Get HTTP method and any body data
    method = os.environ['REQUEST_METHOD']
    if method in ['PUT', 'POST']:
        try:
            data = json.loads(sys.stdin.read())
        except ValueError, e:
            data = list()
            logging.warning('Failed to get data - %s', e)
            error = 'failed to parse json data in body'
        if '_method' in data:                  # for clients that don't support a DELETE, use POST with "_method: delete"
            method = data['_method'].upper()

    # Parse RESTful URI
    uri = urlparse.urlsplit(os.environ['REQUEST_URI'])
    form = urlparse.parse_qs(os.environ['QUERY_STRING'])
    request = method + ' ' + uri.path

    # Connection to MongoDB
    mongo = pymongo.Connection()
    db = mongo.monitoring
    alerts = db.alerts
    mgmt = db.status
    hb = db.heartbeats

    status = dict()
    status['application'] = 'alerta'
    status['time'] = int(time.time() * 1000)

    m = re.search(r'GET /alerta/management/healthcheck$', request)
    if m:
        status['heartbeats'] = list()

        for hb in hb.find({}, {"_id": 0, "type": 0}):
            status['heartbeats'].append(hb)

<<<<<<< HEAD
    for stat in ['OPEN', 'ACK', 'CLOSED', 'DELETED', 'EXPIRED']:
        stat_count = dict()
        stat_count['group'] = "alerts"
        stat_count['name'] = stat.lower()
        stat_count['type'] = "gauge"
        stat_count['title'] = stat + " alerts"
        stat_count['description'] = "Total number of " + stat + " alerts"
        stat_count['value'] = alerts.find({"status": stat}).count()
        status['metrics'].append(stat_count)

    content = json.dumps(status, cls=DateEncoder)
=======
    m = re.search(r'GET /alerta/management/status$', request)
    if m:
        status['metrics'] = list()

        for stat in mgmt.find({}, {"_id": 0}):
            logging.debug('%s', json.dumps(stat))
            status['metrics'].append(stat)
>>>>>>> Add component heartbeats

        for sev in ['CRITICAL', 'MAJOR', 'MINOR', 'WARNING', 'NORMAL', 'INFORM', 'DEBUG']:
            sev_count = dict()
            sev_count['group'] = "alerts"
            sev_count['name'] = sev.lower()
            sev_count['type'] = "gauge"
            sev_count['title'] = "Active " + sev + " alerts"
            sev_count['description'] = "Total number of active " + sev + " alerts"
            sev_count['value'] = alerts.find({"severity": sev}).count()
            status['metrics'].append(sev_count)

        for stat in ['OPEN', 'ACK', 'CLOSED', 'DELETED', 'EXPIRED']:
            stat_count = dict()
            stat_count['group'] = "alerts"
            stat_count['name'] = stat.lower()
            stat_count['type'] = "gauge"
            stat_count['title'] = stat + " alerts"
            stat_count['description'] = "Total number of " + stat + " alerts"
            stat_count['value'] = alerts.find({"status": stat}).count()
            status['metrics'].append(stat_count)

    diff = time.time() - start

    content = json.dumps(status, cls=DateEncoder)
    if 'callback' in form:
        content = '%s(%s);' % (form['callback'][0], content)

    print "Content-Type: application/javascript; charset=utf-8"
    print "Content-Length: %s" % len(content)
    print "Expires: -1"
    print "Cache-Control: no-cache"
    print "Pragma: no-cache"
    print ""
    print content

    logging.info('Request %s completed in %sms', request, diff)

if __name__ == '__main__':
    main()

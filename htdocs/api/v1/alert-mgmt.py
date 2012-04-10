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
import copy
import pymongo
import cgi, cgitb
import logging
import re

__version__ = '1.0'

LOGFILE = '/var/log/alerta/alert-mgmt.log'

# Extend JSON Encoder to support ISO 8601 format dates
class DateEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.isoformat()+'Z'
        else:
            return json.JSONEncoder.default(self, obj)

def main():

    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s alert-mgmt[%(process)d] %(levelname)s - %(message)s", filename=LOGFILE)

    # Connection to MongoDB
    mongo = pymongo.Connection()
    db = mongo.monitoring
    alerts = db.alerts
    mgmt = db.status

    status = dict()
    status['metrics'] = list()
    status['application'] = 'alerta'
    status['time'] = int(time.time() * 1000)

    for stat in mgmt.find({}, {"_id": 0}):
        logging.debug('%s', json.dumps(stat))
        status['metrics'].append(stat)

    for sev in ['CRITICAL', 'MAJOR', 'MINOR', 'WARNING', 'NORMAL', 'INFORM', 'DEBUG']:
        sev_count = dict()
        sev_count['group'] = "alerts"
        sev_count['name'] = sev.lower()
        sev_count['type'] = "gauge"
        sev_count['title'] = "Active " + sev + " alerts"
        sev_count['description'] = "Total number of active " + sev + " alerts"
        sev_count['value'] = alerts.find({"severity": sev}).count()
        status['metrics'].append(sev_count)

    content = json.dumps(status, cls=DateEncoder)

    # logging.debug('API >>> %s', content)

    print "Content-Type: application/javascript; charset=utf-8"
    print "Content-Length: %s" % len(content)
    print "Expires: -1"
    print "Cache-Control: no-cache"
    print "Pragma: no-cache"
    print ""
    print content

if __name__ == '__main__':
    main()

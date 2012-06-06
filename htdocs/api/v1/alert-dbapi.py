#!/usr/bin/env python
########################################
#
# alerta-dbapi.py - Alerter DB API
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

__version__ = '1.2'

LOGFILE = '/var/log/alerta/alert-dbapi.log'

# Extend JSON Encoder to support ISO 8601 format dates
class DateEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.isoformat()+'Z'
        else:
            return json.JSONEncoder.default(self, obj)

def main():

    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s alert-dbapi[%(process)d] %(levelname)s - %(message)s", filename=LOGFILE)

    cgiform = cgi.FieldStorage() # only used by POST to smuggle 'delete' as "_method" variable
    callback = None

    # Connection to MongoDB
    mongo = pymongo.Connection()
    db = mongo.monitoring
    alerts = db.alerts
    mgmt = db.status

    for e in os.environ:
        logging.info('%s: %s', e, os.environ[e])

    total = 0
    status = dict()
    start = time.time()
    status['response'] = dict()
    status['response']['status'] = 'failed' # assume 'failed', unless a response overwrites with 'ok'

    if 'REQUEST_URI' in os.environ and 'REQUEST_METHOD' in os.environ:

        if os.environ['REQUEST_URI'].startswith('/alerta/api/v1/alerts/alert/'):

            if os.environ['REQUEST_METHOD'] == 'GET':

                # REQUEST_URI: /alerta/api/v1/alerts/alert/3bfd0f9d-2843-419d-9d4d-c99079a39d36
                # QUERY_STRING: id=3bfd0f9d-2843-419d-9d4d-c99079a39d36 (after RewriteRule applied)

                queryStr = os.environ['QUERY_STRING']
                form = dict([queryParam.split('=') for queryParam in queryStr.split('&')])
                form['_id'] = form['id']
                del form['id'] 
                logging.info('form %s', json.dumps(form))

                status['response']['alert'] = list()

                logging.debug('MongoDB GET -> alerts.find_one(%s)', form)
                alert = alerts.find_one(form)
                if alert:
                    alert['id'] = alert['_id']
                    del alert['_id']
                    status['response']['alert'] = alert
                    status['response']['status'] = 'ok'
                    total = 1
                else:
                    status['response']['alert'] = None
                    status['response']['status'] = 'not found'
                    total = 0

                diff = time.time() - start
                status['response']['time'] = "%.3f" % diff
                status['response']['total'] = total
                status['response']['localTime'] = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

                diff = int(diff * 1000) # XXX - management status needs time in milliseconds
                mgmt.update(
                    { "group": "requests", "name": "simple_get", "type": "counter", "title": "Simple GET requests", "description": "Requests to the alert status API" },
                    { '$inc': { "count": 1, "totalTime": diff}},
                    True)

            elif os.environ['REQUEST_METHOD'] == 'PUT':

                logging.info('PUT %s', cgiform.getvalue("id"))
                form = dict()
                update = dict()
                for field in cgiform.keys():
                    if field == 'id':
                        form['_id'] = cgiform.getvalue("id")
                    else:
                        update[field] = cgiform.getvalue(field)

                logging.debug('MongoDB MODIFY -> alerts.update(%s { $set: %s })', form, update)
                status['response']['status'] = alerts.update(form, { '$set': update })

                diff = time.time() - start
                status['response']['time'] = "%.3f" % diff
                status['response']['localTime'] = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

                diff = int(diff * 1000) # XXX - management status needs time in milliseconds
                mgmt.update(
                    { "group": "requests", "name": "update", "type": "timer", "title": "PUT requests", "description": "Requests to update alerts via the API" },
                    { '$inc': { "count": 1, "totalTime": diff}},
                    True)

            # elif os.environ['REQUEST_METHOD'] == 'DELETE':
            elif os.environ['REQUEST_METHOD'] == 'POST' and cgiform.getvalue("_method") == 'delete':

                logging.info('DELETE %s', cgiform.getvalue("id"))
                form = dict()
                form['_id'] = cgiform.getvalue("id")
                
                logging.debug('MongoDB DELETE -> alerts.remove(%s)', form)
                status['response']['status'] = alerts.remove(form, safe=True)

                diff = time.time() - start
                status['response']['time'] = "%.3f" % diff
                status['response']['localTime'] = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

                diff = int(diff * 1000) # XXX - management status needs time in milliseconds
                mgmt.update(
                    { "group": "requests", "name": "delete", "type": "timer", "title": "DELETE requests", "description": "Requests to delete alerts via the API" },
                    { '$inc': { "count": 1, "totalTime": diff}},
                    True)

        if os.environ['REQUEST_URI'].startswith('/alerta/api/v1/alerts?'):

            # REQUEST_URI: /alerta/api/v1/alerts?environment=PROD&service=R2&sort-by=lastReceiveTime
            # QUERY_STRING: environment=PROD&service=R2&sort-by=lastReceiveTime

            queryStr = os.environ['QUERY_STRING']
            form = dict([queryParam.split('=') for queryParam in queryStr.split('&')])

            if 'callback' in form:
                callback = form['callback']
                del form['callback']
            if 'hide-alert-details' in form:
                hide_details = form['hide-alert-details'] == 'true'
                del form['hide-alert-details']
            else:
                hide_details = False
            if '_' in form:
                del form['_']
            if 'id' in form:
                form['_id'] = form['id']
                del form['id']

            sortby = list()
            if 'sort-by' in form:
                for s in form['sort-by'].split('+'):
                    sortby.append((s,-1)) # assume descending ie for dates that would be newest first
                del form['sort-by']
                logging.info('%s', json.dumps(sortby))

            logging.info('%s', json.dumps(form))
    
            alertDetails = list()
            logging.debug('MongoDB -> alerts.find(%s, sort=%s)', form, sortby)
            for alert in alerts.find(form, sort=sortby):
                if not hide_details:
                    alert['id'] = alert['_id']
                    del alert['_id']
                    alertDetails.append(alert)

            form['severity'] = 'CRITICAL'
            critical = alerts.find(form).count()
            form['severity'] = 'MAJOR'
            major = alerts.find(form).count()
            form['severity'] = 'MINOR'
            minor = alerts.find(form).count()
            form['severity'] = 'WARNING'
            warning = alerts.find(form).count()
            form['severity'] = 'NORMAL'
            normal = alerts.find(form).count()
            form['severity'] = 'INFORM'
            inform = alerts.find(form).count()
            form['severity'] = 'DEBUG'
            debug = alerts.find(form).count()

            sev = { 'critical': critical,
                    'major': major,
                    'minor': minor,
                    'warning': warning,
                    'normal': normal,
                    'inform': inform,
                    'debug': debug
            }
            logging.debug('severityCounts %s', sev)

            a = { 'severityCounts': sev , 'alertDetails': list(alertDetails) }
            status['response']['alerts'] = list()
            status['response']['alerts'].append(a)
    
            diff = time.time() - start
            status['response']['status'] = 'ok'
            status['response']['time'] = "%.3f" % diff
            status['response']['total'] = critical + major + minor + warning + normal + inform + debug
            status['response']['localTime'] = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    
            diff = int(diff * 1000) # XXX - management status needs time in milliseconds
            mgmt.update(
                { "group": "requests", "name": "complex_get", "type": "timer", "title": "Complex GET requests", "description": "Requests to the alert status API" },
                { '$inc': { "count": 1, "totalTime": diff}},
                True)

        content = json.dumps(status, cls=DateEncoder)
        if callback is not None:
            content = '%s(%s);' % (callback, content)

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

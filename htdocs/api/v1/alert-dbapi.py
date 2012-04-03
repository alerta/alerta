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

# Extend JSON Encoder to support ISO 8601 format dates
class DateEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.isoformat()
        else:
            return json.JSONEncoder.default(self, obj)

def main():

    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s alert-dbapi[%(process)d] %(levelname)s Thread-%(thread)d - %(message)s", filename='/tmp/alert-dbapi.log', filemode='a')

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
                # QUERY_STRING: _id=3bfd0f9d-2843-419d-9d4d-c99079a39d36 (after RewriteRule applied)

                queryStr = os.environ['QUERY_STRING']
                form = dict([queryParam.split('=') for queryParam in queryStr.split('&')])
                logging.info('form %s', json.dumps(form))

                status['response']['alert'] = list()

                logging.debug('MongoDB GET -> alerts.find_one(%s, {"_id": 0})', form)
                alert = alerts.find_one(form, {"_id": 0})
                if alert:
                    alert['id'] = form['_id']
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
                    { "group": "requests", "name": "api", "type": "counter", "title": "API requests", "description": "Requests to the alert status API" },
                    { '$inc': { "count": 1, "totalTime": diff}},
                    True)

            # elif os.environ['REQUEST_METHOD'] == 'DELETE':
            elif os.environ['REQUEST_METHOD'] == 'POST' and cgiform.getvalue("_method") == 'delete':

                logging.info('DELETE %s', cgiform.getvalue("id"))
                form = dict()
                form['lastReceiveId'] = cgiform.getvalue("_id")
                
                logging.debug('MongoDB DELETE -> alerts.remove(%s)', form)
                status['response']['status'] = alerts.remove(form, safe=True)

                diff = time.time() - start
                status['response']['time'] = "%.3f" % diff
                status['response']['localTime'] = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

                diff = int(diff * 1000) # XXX - management status needs time in milliseconds
                mgmt.update(
                    { "group": "requests", "name": "api", "type": "counter", "title": "API requests", "description": "Requests to the alert status API" },
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
            if '_' in form:
                del form['_']

            sortby = list()
            if 'sort-by' in form:
                for s in form['sort-by'].split('+'):
                    sortby.append((s,-1)) # assume descending ie for dates that would be newest first
                del form['sort-by']
                logging.info('%s', json.dumps(sortby))

            logging.info('%s', json.dumps(form))
    
            status['response']['alerts'] = list()

            sevCounts = dict()
            alertDetails = dict()
            logging.debug('MongoDB -> alerts.find(%s, {"_id": 0}, sort=%s)', form, sortby)
            for alert in alerts.find(form, {"_id": 0}, sort=sortby):
                host = alert['resource']
                env = alert['environment']
                svc = alert['service']
                sev = alert['severity']
                evt = alert['event']
    
                if (env,svc) not in sevCounts:
                    sevCounts[(env,svc)] = dict()
                    sevCounts[(env,svc)][sev] = 1
                elif sev not in sevCounts[(env,svc)]:
                    sevCounts[(env,svc)][sev] = dict()
                    sevCounts[(env,svc)][sev] = 1
                else:
                    sevCounts[(env,svc)][sev] += 1
                total += 1
    
                if (env,svc) not in alertDetails:
                    alertDetails[(env,svc)] = list()
                alertDetails[(env,svc)].append(alert)
            
            for env,svc in sevCounts.keys():
                sev = { 'critical': sevCounts[(env,svc)].get(('CRITICAL'), 0),
                        'major': sevCounts[(env,svc)].get(('MAJOR'), 0),
                        'minor': sevCounts[(env,svc)].get(('MINOR'), 0), 
                        'warning': sevCounts[(env,svc)].get(('WARNING'), 0),
                        'normal': sevCounts[(env,svc)].get(('NORMAL'), 0) }
                a = { 'environment': env, 'service': svc, 'severityCounts': sev , 'alertDetails': list(alertDetails[(env,svc)]) }
                status['response']['alerts'].append(a)
    
            diff = time.time() - start
            status['response']['status'] = 'ok'
            status['response']['time'] = "%.3f" % diff
            status['response']['total'] = total
            status['response']['localTime'] = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    
            diff = int(diff * 1000) # XXX - management status needs time in milliseconds
            mgmt.update(
                { "group": "requests", "name": "api", "type": "counter", "title": "API requests", "description": "Requests to the alert status API" },
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

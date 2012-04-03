#!/usr/bin/env python
########################################
#
# alerta-treemap.py - Alerter Treemap API
#
########################################

import os, sys
import time
import re
try:
    import json
except ImportError:
    import simplejson as json

import datetime
import copy
import pymongo
import cgi, cgitb
import logging

__version__ = '1.2'

LOGFILE = '/var/log/alerta/alert-treemap.log'

# Extend JSON Encoder to support ISO 8601 format dates
class DateEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.isoformat()
        else:
            return json.JSONEncoder.default(self, obj)

def main():

    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s alert-treemap[%(process)d] %(levelname)s - %(message)s", filename=LOGFILE)

    form = dict()
    callback = None

    # Connection to MongoDB
    mongo = pymongo.Connection()
    db = mongo.monitoring
    alerts = db.alerts
    mgmt = db.status

    for e in os.environ:
        logging.info('%s: %s', e, os.environ[e])

    if 'REQUEST_URI' in os.environ:
        path = os.environ['REQUEST_URI']

        if path.endswith('/alerta/management/status'):
            status = dict()
            status['metrics'] = list()
            status['application'] = "alert-cgi"
            for m in mgmt.find({}, {"_id": 0}):
                status['metrics'].append(m)
            status['time'] = int(time.time())

        # elif path.startswith('/alerta/v1/alert-data'):
        else:

            if os.environ['REQUEST_URI'].find('?') > -1:
                queryStr = os.environ['REQUEST_URI'].split('?')[1]
                form = dict([queryParam.split('=') for queryParam in queryStr.split('&')])

            if 'callback' in form:
                callback = form['callback']
                del form['callback']
            if '_' in form:
                del form['_']

            logging.info('%s', json.dumps(form))
    
            total = 0
            status = dict()
            start = time.time()
            status['response'] = dict()
            status['response']['treemap'] = dict()
            status['response']['treemap']['name'] = 'alerts'
            status['response']['treemap']['children'] = list()

            envChildren = dict()
            svcChildren = dict()
            sevChildren = dict()

            envloop = dict()
            svcloop = dict()

            sevCounts = dict()
            logging.debug('MongoDB -> alerts.find(%s, {"_id": 0})', form)
            for alert in alerts.find(form, {"_id": 0}):
                host = alert['resource']
                env = alert['environment']
                svc = alert['service']
                sev = alert['severity']
                evt = alert['event']
                # print "env = %s , svc = %s" % (env,svc)
    
                if (env,svc) not in sevCounts:
                    sevCounts[(env,svc)] = dict()
                    sevCounts[(env,svc)][sev] = 1
                elif sev not in sevCounts[(env,svc)]:
                    sevCounts[(env,svc)][sev] = dict()
                    sevCounts[(env,svc)][sev] = 1
                else:
                    sevCounts[(env,svc)][sev] += 1
                total += 1

                if env not in envChildren:
                    envloop[env] = 1
                if svc not in svcChildren:
                    svcloop[svc] = 1

                if (env,svc) not in svcChildren:
                    svcChildren[(env,svc)] = list()

            envtree = dict()
            for env in envloop:
                envtree[env] = dict()
                envtree[env]['name'] = env
                envtree[env]['children'] = list()
                for svc in svcloop:
                    if (env,svc) in svcChildren:
                        # logging.debug('env %s, svc %s', env, svc)
                        sev = [
                            { 'name': 'critical', 'description': env+' '+svc, 'size': sevCounts[(env,svc)].get(('CRITICAL'), 0), },
                            { 'name': 'major',    'description': env+' '+svc, 'size': sevCounts[(env,svc)].get(('MAJOR'), 0), },
                            { 'name': 'minor',    'description': env+' '+svc, 'size': sevCounts[(env,svc)].get(('MINOR'), 0), }, 
                            { 'name': 'warning',  'description': env+' '+svc, 'size': sevCounts[(env,svc)].get(('WARNING'), 0), },
                            { 'name': 'normal',   'description': env+' '+svc, 'size': sevCounts[(env,svc)].get(('NORMAL'), 0) }
                        ]
                        envtree[env]['children'].append({ 'name': svc, 'children': [ { 'name': 'severity', 'children': list(sev) } ] })

                status['response']['treemap']['children'].append(envtree[env])
    
            diff = time.time() - start
            status['response']['status'] = 'ok'
            status['response']['time'] = "%.3f" % diff
            status['response']['total'] = total
            status['response']['localTime'] = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    
            diff = int(diff * 1000) # XXX - management status needs time in milliseconds
            mgmt.update(
                { "group": "requests", "name": "treemap", "type": "counter", "title": "Treemap requests", "description": "Requests to the alert treemap API" },
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

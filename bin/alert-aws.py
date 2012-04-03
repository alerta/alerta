#!/usr/bin/env python

########################################
#
# alert-aws.py - Amazon Web Service Alert Adapter
#
# Written by Nick Satterly (Mar 2012)
# 
########################################

import os, sys
import optparse
try:
    import json
except ImportError:
    import simplejson as json
import datetime, time
from optparse import OptionParser

# STOMP bindings from https://github.com/mozes/stompest
from stompest.simple import Stomp
import logging
import uuid
import boto.ec2

BROKER  = 'devmonsvr01:61613'
QUEUE   = '/queue/prod.alerts'
LOGFILE = '/tmp/alert-aws.log'

Version = '1.0, 16/03/2012'

def main():

    loglevel = logging.INFO
    logging.basicConfig(level=loglevel, format="%(asctime)s alert-aws[%(process)d] %(levelname)s Thread-%(thread)d - %(message)s", filename=LOGFILE, filemode='a')

    print '%-10s %11s %20s %25s %25s' % ('ec2-zone', 'instance-id', 'state (code)', 'reachability', 'instance-status')
    print '%s %s %s %s %s' % ('-'*10, '-'*11, '-'*20, '-'*25, '-'*25)
    regions = boto.ec2.regions()
    for r in regions:
        conn = r.connect()
        stats = conn.get_all_instance_status()
        for s in stats:
            print '%10s %11s %20s %25s %25s' % (s.zone, s.id, s.state_name+' ('+str(s.state_code)+')', s.system_status, s.instance_status)

    sys.exit()


    regions = boto.ec2.regions()
    eu = regions[0]
    conn = eu.connect()
    stats = conn.get_all_instance_status()

    for s in stats:
        print 'instance %s status %s' % (s.id, s.state_name)

    sys.exit()


    alertid = str(uuid.uuid4()) # random UUID

    headers = dict()
    headers['type'] = "text"
    headers['correlation-id'] = alertid

    alert = dict()
    alert['id']          = alertid
    alert['resource']    = options.environment.lower()+'.'+options.service.lower()+'.'+options.resource
    alert['event']       = options.event
    alert['group']       = options.group
    alert['value']       = options.value
    alert['severity']    = options.severity.upper()
    if options.previousSeverity:
        alert['previousSeverity']    = options.previousSeverity.upper()
    alert['environment'] = options.environment.upper()
    alert['service']     = options.service
    alert['text']        = options.text
    alert['type']        = 'exceptionAlert'
    alert['tags']        = options.tags
    alert['summary']     = '%s - %s %s is %s on %s %s' % (options.environment, options.severity, options.event, options.value, options.service, os.uname()[1])
    alert['createTime']  = datetime.datetime.now().isoformat()
    alert['origin']      = 'alert-cli/%s' % os.uname()[1]
    alert['repeat']      = options.repeat

    logging.info('ALERT: %s', json.dumps(alert))

    if (not options.dry_run):
        broker, port = BROKER.split(':')
        stomp = Stomp(broker, int(port))
        try:
            stomp.connect()
        except Exception, e:
            print >>sys.stderr, "ERROR: Could not connect to broker %s - %s" % (BROKER, e)
            logging.error('ERROR: Could not connect to to broker %s - %s', BROKER, e)
            sys.exit(1)
        try:
            stomp.send(QUEUE, json.dumps(alert), headers)
        except Exception, e:
            print >>sys.stderr, "ERROR: Failed to send alert to broker %s - %s " % (BROKER, e)
            logging.error('ERROR: Failed to send alert to broker %s - %s', BROKER, e)
            sys.exit(1)
        stomp.disconnect()
        print alertid
        sys.exit(0)
    else:
        print "%s %s" % (json.dumps(headers,indent=4), json.dumps(alert))
        # print "%s %s" % (json.dumps(headers,indent=4), json.dumps(alert,indent=4))

if __name__ == '__main__':
    main()

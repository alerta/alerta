#!/usr/bin/env python
########################################
#
# alert-twitter.py - Alert Twitter module
#
########################################

import os
import sys
import time
try:
    import json
except ImportError:
    import simplejson as json
import stomp
import datetime
import logging
import pycurl
import urllib2
import re

__version__ = "1.0"

TWITTER_STREAM = 'https://stream.twitter.com/1/statuses/filter.json'
TWITTER_USERNAME = 'nicksatterly'
TWITTER_PASSWORD = 'tw33tm3'

TRACK = 'guardian website down'

LOGFILE = '/var/log/alerta/alert-twitter.log'
PIDFILE = '/var/run/alerta/alert-twitter.pid'

ES_SERVER   = 'devmonsvr01'
ES_BASE_URL = 'http://%s:9200/logstash' % (ES_SERVER)

class StatusHandler(object):

    def __init__(self):

        self.conn = pycurl.Curl()
        self.conn.setopt(pycurl.VERBOSE, 1)
        self.conn.setopt(pycurl.HTTPAUTH, pycurl.HTTPAUTH_BASIC)
        self.conn.setopt(pycurl.POST, 1)
        self.conn.setopt(pycurl.POSTFIELDS, "track=%s" % TRACK)
        self.conn.setopt(pycurl.USERPWD, "%s:%s" % (TWITTER_USERNAME, TWITTER_PASSWORD))
        self.conn.setopt(pycurl.URL, TWITTER_STREAM)
        self.conn.setopt(pycurl.WRITEFUNCTION, self.on_status)
        
        try:
            self.conn.perform()
        except BaseException, e:
            logging.error('Problem with twitter stream : %s', e)

        self.conn.close()
        self.__init__()

    def on_status(self, body):

        if body == '\r\n':
            logging.debug("Received heartbeat")
            return

        tags = list()
        tweet = dict()
        tweet = json.loads(body)

        if 'text' not in tweet:
            logging.debug("Not a tweet; %s", body)
            return

        logging.debug("Received tweet; %s", body)

        # Only log certain fields
        fields = dict()
        fields['screen_name'] = tweet['user']['screen_name']
        fields['text'] = tweet['text']
        fields['time_zone'] = tweet['user']['time_zone']
        for ht in tweet['entities']['hashtags']:
            tags.append('#'+ht['text'])
        fields['tags'] = ' '.join(tags)
        fields['createTime'] = datetime.datetime.strptime(tweet['created_at'], '%a %b %d %H:%M:%S +0000 %Y').isoformat()+'+00:00'

        # Index tweets in ElasticSearch using Logstash format so that logstash GUI and/or Kibana can be used as frontend
        logstash = dict() 
        logstash['@message']     = tweet['text']
        logstash['@source']      = tweet['source']
        logstash['@source_host'] = 'not_used'
        logstash['@source_path'] = 'stream.twitter.com'
        logstash['@tags']        = ' '.join(tags)
        logstash['@timestamp']   = datetime.datetime.utcnow().isoformat()+'+00:00'
        logstash['@type']        = 'tweet'
        logstash['@fields']      = fields

        try:
            url = "%s/%s" % (ES_BASE_URL, 'tweet')
            response = urllib2.urlopen(url, json.dumps(logstash)).readlines()
            id = json.loads(''.join(response))['_id']
        except Exception, e:
            logging.error('%s : Tweet indexing failed %s %s %s %s', tweet['id_str'], e, url, json.dumps(response), json.dumps(logstash))
            return

        logging.info('%s : Tweet indexed at %s/%s/%s', tweet['id_str'], ES_BASE_URL, 'tweet', id)
        
def main():

    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s alert-twitter[%(process)d] %(levelname)s - %(message)s", filename=LOGFILE)
    logging.info('Starting up Alert Twitter version %s', __version__)

    # Write pid file
    if os.path.isfile(PIDFILE):
        logging.error('%s already exists, exiting' % PIDFILE)
        sys.exit()
    else:
        file(PIDFILE, 'w').write(str(os.getpid()))

    # Connect to Twitter stream
    status = StatusHandler()

    while True:
        try:
            time.sleep(0.01)
        except KeyboardInterrupt, SystemExit:
            os.unlink(PIDFILE)
            sys.exit()

if __name__ == '__main__':
    main()

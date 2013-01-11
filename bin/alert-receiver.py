#!/usr/bin/env python
########################################
#
# alert-receiver.py - Alert Receiver
#
########################################

import socket
import time
import simplejson as json
import os
import sys
import logging
import stomp
import yaml
import threading
import select
import uuid
import datetime
import errno
import re

__program__ = 'alert-receiver'
__version__ = '1.0.4'


BROKER_LIST  = [('localhost', 61613)] # list of brokers for failover                                                                                                                                                                                                 
ALERT_QUEUE  = '/queue/alerts'
LOGFILE = '/var/log/alerta/alert-receiver.log'
PIDFILE = '/var/run/alerta/alert-receiver.pid'
CONFIGFILE = '/opt/alerta/conf/alert-receiver.yaml'

config = dict()
sock = list()

def init_config():

    global config

    logging.info('Loading config...')

    try:
        config = yaml.load(open(CONFIGFILE))
    except Exception, e:
        logging.error('Failed to load config: %s', e)
    logging.info('Loaded %d config OK', len(config))

def send_heartbeat():

    heartbeatid = str(uuid.uuid4()) # random UUID
    createTime = datetime.datetime.utcnow()

    headers = dict()
    headers['type']           = "heartbeat"
    headers['correlation-id'] = heartbeatid

    heartbeat = dict()
    heartbeat['id']         = heartbeatid
    heartbeat['type']       = "heartbeat"
    heartbeat['createTime'] = createTime.replace(microsecond=0).isoformat() + ".%03dZ" % (createTime.microsecond//1000)
    heartbeat['origin']     = "%s/%s" % (__program__,os.uname()[1])
    heartbeat['version']    = __version__

    conn.send(json.dumps(heartbeat), headers, destination=ALERT_QUEUE)
    broker = conn.get_host_and_port()
    logging.info('%s : Sending heartbeat from the receiver to %s: %s', heartbeat['id'], broker[0], str(broker[1]))

def disconnect():
 
    global sock

    for s in sock:
        s.close()

def connect():

    global sock
    
    for item in config:
        while True:
            try:
                HOST, PORT = item['host'], item['port']
                ADDR = (HOST, PORT)
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect((ADDR))
                sock.append(s)
                logging.info('Connecting to %s port %s' % (HOST, PORT))
                break
            except socket.error, e:
                if e.errno == errno.ECONNREFUSED :
                    logging.error('Server %s is not ready. Retrying later in 20 seconds.' % HOST)
                    time.sleep(20)
                    continue
                else:
                   logging.error('Connection error to %s port %s' % (HOST, PORT))
                   sys.exit(2)

class ConcatJSONDecoder(json.JSONDecoder):

    FLAGS = re.VERBOSE | re.MULTILINE | re.DOTALL
    WHITESPACE = re.compile(r'[ \t\n\r]*', FLAGS)

    def decode(self, s, _w=WHITESPACE.match):
        s_len = len(s)

        objs = []
        end = 0
        while end != s_len:
            obj, end = self.raw_decode(s, idx=_w(s, end).end())
            end = _w(s, end).end()
            objs.append(obj)
        return objs

def main():

    global conn, sock

    logging.basicConfig(level=logging.INFO, format="%(asctime)s alert-receiver[%(process)d] %(threadName)s %(levelname)s - %(message)s", filename=LOGFILE)
    logging.info('Starting up Alerta Poller version %s', __version__)

    # Write pid file if not already running
    if os.path.isfile(PIDFILE):
        pid = open(PIDFILE).read()
        try:
            os.kill(int(pid), 0)
            logging.error('Process with pid %s already exists, exiting', pid)
            sys.exit(1)
        except OSError:
            pass
    file(PIDFILE, 'w').write(str(os.getpid()))

    # Initialiase config
    init_config()
    config_mod_time = os.path.getmtime(CONFIGFILE)

    # Connect to message broker
    try:
        conn = stomp.Connection(BROKER_LIST)
        conn.start()
        conn.connect(wait=True)
    except Exception, e:
        logging.error('Could not connect to broker %s', e)
        sys.exit(1)

    # Connect to servers to get messages
    connect()

    while True:
        try:
            # Read (or re-read) config as necessary
            if os.path.getmtime(CONFIGFILE) != config_mod_time:
                init_config()
                config_mod_time = os.path.getmtime(CONFIGFILE)

                #Close connections and re-open on new config file
                disconnect()
                connect()     

            logging.info('Waiting on select ...')
            ip, op, rdy = select.select(sock, [], [])
            logging.info('Select finished!')

            for i in ip:
                alerts = list()
                buf = ''
                counter = 0
                while True:
                    try:
                        data = i.recv(1024*4)
                    except socket.error:
                        logging.error('Error receiving from server')
                    logging.info('DATA >>>>%s<<<<', data)
                    if data == '':
                        logging.debug('Break emtpy buffer')
                        counter += 1
                        break
                    buf += data
                    try:
                        alerts = json.loads(buf, cls=ConcatJSONDecoder)
                        logging.info('JSON OK!')
                        break
                    except:
                        logging.info('JSON BAD!')
                        pass

                if counter == 3:
                    logging.error('Server has gone away. Trying reconnecting ...')
                    disconnect()
                    connect()

                logging.info('Received %s alerts', len(alerts))
                if len(alerts) > 0:
                    logging.info('%s of alerts readed from the buffer', len(alerts))
                    for alert in alerts:
                        logging.info('Received alert message: %s', alert)
                        if 'type' in alert and 'id' in alert:
                            headers = dict()
                            headers['type']           = alert['type']
                            headers['correlation-id'] = alert['id']
                            conn.send(json.dumps(alert), headers, destination=ALERT_QUEUE)
                            broker = conn.get_host_and_port()
                            logging.info('%s : Alert sent to %s:%s', alert['id'], broker[0], str(broker[1]))
                        else:
                            logging.error('Skipping malformed alert')
                else:
                    logging.debug('No data!')

            send_heartbeat()

        except (KeyboardInterrupt, SystemExit):
            disconnect()
            os.unlink(PIDFILE)
            logging.info('Graceful exit.')
            sys.exit(0)
            conn.disconnect()
            sys.exit(0)

if __name__ == '__main__':
      main()

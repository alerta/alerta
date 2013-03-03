import os
import sys
import time

try:
    import json
except:
    import simplejson as json
import threading
import yaml
import datetime
import logging
import uuid
import re
from Queue import Queue
import socket
from dynect.DynectDNS import DynectRest

Version = '2.0.0'

BROKER_LIST = [('localhost', 61613)] # list of brokers for failover
ALERT_QUEUE = '/queue/alerts'
GLOBAL_CONF = '/opt/alerta/alerta/alerta-global.yaml'
DEFAULT_TIMEOUT = 86400
CONFIGFILE = '/opt/alerta/alerta/alert-dynect.yaml'
DISABLE = '/opt/alerta/alerta/alert-dynect.disable'
LOGFILE = '/var/log/alerta/alert-dynect.log'
PIDFILE = '/var/run/alerta/alert-dynect.pid'

ADDR = ''
PORT = 29876
BIND_ADDR = (ADDR, PORT)
BUFSIZE = 4096

REPEAT_LIMIT = 10
count = 0

_check_rate = 120             # Check rate of alerts

# Global variables
config = dict()
info = dict()
last = dict()
globalconf = dict()
alert_queue = Queue()
conn = list()

SEVERITY_CODE = {
    # ITU RFC5674 -> Syslog RFC5424
    'CRITICAL': 1, # Alert
    'MAJOR': 2, # Crtical
    'MINOR': 3, # Error
    'WARNING': 4, # Warning
    'NORMAL': 5, # Notice
    'INFORM': 6, # Informational
    'DEBUG': 7, # Debug
}


class QueueThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        while True:
            alert = alert_queue.get()
            for c in conn:
                try:
                    c.sendall(alert)
                    logging.info('Sending %s' % alert)
                    logging.info('alert sent to %s' % c)
                except:
                    logging.info('Problem sending alert. No client ready to receive.')
            alert_queue.task_done()


class WorkerThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        global count, last

        while True:

            queryDynect()

            logging.info('Repeats: %d' % count)

            for item in info:

                # Defaults
                resource = item
                group = 'GSLB'
                value = info[item][0]
                environment = ['PROD']
                service = ['Network']
                tags = ''
                correlate = ''
                event = ''
                text = 'Item was %s now it is %s.' % (info[item][0], last[item][0])

                if last[item][0] != info[item][0] or count == repeats:

                    if item.startswith('gslb-'):

                        # gslb status       = ok | unk | trouble | failover

                        logging.info('GSLB state change from %s to %s' % (info[item][0], last[item][0]))
                        text = 'GSLB status is %s.' % last[item][0]

                        if 'ok' in info[item][0]:
                            event = 'GslbOK'
                            severity = 'NORMAL'
                        else:
                            event = 'GslbNotOK'
                            severity = 'CRITICAL'

                    elif item.startswith('pool-'):

                        # pool status       = up | unk | down
                        # pool serve_mode   = obey | always | remove | no
                        # pool weight	(1-15)

                        logging.info('Pool state change from %s to %s' % (info[item][0], last[item][0]))

                        if 'up:obey' in info[item][0] and checkweight(info[item][1], item) == True:
                            event = 'PoolUp'
                            severity = 'NORMAL'
                            text = 'Pool status is normal'
                        else:
                            if 'down' in info[item][0]:
                                event = 'PoolDown'
                                severity = 'MAJOR'
                                text = 'Pool is down'
                            elif 'obey' not in info[item][0]:
                                event = 'PoolServe'
                                severity = 'MAJOR'
                                text = 'Pool with an incorrect serve mode'
                            elif checkweight(info[item][1], item) == False:
                                event = 'PoolWeightError'
                                severity = 'MINOR'
                                text = 'Pool with an incorrect weight'

                    alertid = str(uuid.uuid4()) # random UUID
                    createTime = datetime.datetime.utcnow()

                    headers = dict()
                    headers['type'] = "serviceAlert"
                    headers['correlation-id'] = alertid

                    alert = dict()
                    alert['id'] = alertid
                    alert['resource'] = resource
                    alert['event'] = event
                    alert['group'] = group
                    alert['value'] = value
                    alert['severity'] = severity.upper()
                    alert['severityCode'] = SEVERITY_CODE[alert['severity']]
                    alert['environment'] = environment
                    alert['service'] = service
                    alert['text'] = text
                    alert['type'] = 'dynectAlert'
                    alert['tags'] = tags
                    alert['summary'] = '%s - %s %s is %s on %s %s' % (
                    ','.join(environment), severity.upper(), event, value, ','.join(service), resource)
                    alert['createTime'] = createTime.replace(microsecond=0).isoformat() + ".%03dZ" % (
                    createTime.microsecond // 1000)
                    alert['origin'] = "%s/%s" % (__program__, os.uname()[1])
                    alert['thresholdInfo'] = 'n/a'
                    alert['timeout'] = DEFAULT_TIMEOUT
                    alert['correlatedEvents'] = correlate

                    logging.info('%s : %s', alertid, json.dumps(alert))

                    alert_queue.put(json.dumps(alert))
                    logging.info('%s : Alert sent to client' % alertid)

            last = info.copy()

            if count:
                count -= 1
            else:
                count = repeats

            send_heartbeat()

            # Check the internal queue
            logging.info('Sleeping for %s secs.' % _check_rate)
            time.sleep(_check_rate)

# Initialise Config
def init_config():
    global config, repeats, count, last

    logging.info('Loading config...')

    try:
        config = yaml.load(open(CONFIGFILE))
    except Exception, e:
        logging.error('Failed to load config: %s', e)
    logging.info('Loaded %d config OK', len(config))

    repeats = config.get('repeats', REPEAT_LIMIT)
    count = repeats

    del config['repeats']

    queryDynect()

    last = info.copy()


def checkweight(parent, resource):
    weight = info[resource][0].split(':')[2]
    for item in info:
        if item.startswith('pool-') and info[item][1] == parent and item != resource and weight ==
                info[item][0].split(':')[2]:
            return True
            break
    return False


def queryDynect():
    global info

    logging.info('Quering DynECT to get the state of GSLBs')

    # Creating DynECT API session
    try:

        rest_iface = DynectRest()

        response = rest_iface.execute('/Session/', 'POST', config)

        if response['status'] != 'success':
            logging.error('Incorrect credentials')
            sys.exit(1)

        # Discover all the Zones in DynECT
        response = rest_iface.execute('/Zone/', 'GET')
        zone_resources = response['data']

        # Discover all the LoadBalancers
        for item in zone_resources:
            zone = item.split('/')[3]
            response = rest_iface.execute('/LoadBalance/' + zone + '/', 'GET')
            gslb = response['data']

            # Discover LoadBalancer pool information.
            for lb in gslb:
                fqdn = lb.split('/')[4]
                response = rest_iface.execute('/LoadBalance/' + zone + '/' + fqdn + '/', 'GET')
                info['gslb-' + fqdn] = response['data']['status'], 'gslb-' + fqdn

                for i in response['data']['pool']:
                    name = '%s-%s' % (fqdn, i['label'].replace(' ', '-'))
                    state = '%s:%s:%s' % (i['status'], i['serve_mode'], i['weight'])
                    parent = 'gslb-' + fqdn
                    info['pool-' + name] = state, parent

        logging.info('Finish quering and object discovery.')
        logging.info('GSLBs and Pools: %s', json.dumps(info))

        rest_iface.execute('/Session/', 'DELETE')

    except Exception, e:
        logging.error('Failed to discover GSLBs: %s', e)
        pass


def send_heartbeat():
    heartbeatid = str(uuid.uuid4()) # random UUID
    createTime = datetime.datetime.utcnow()

    headers = dict()
    headers['type'] = "heartbeat"
    headers['correlation-id'] = heartbeatid

    heartbeat = dict()
    heartbeat['id'] = heartbeatid
    heartbeat['type'] = "heartbeat"
    heartbeat['createTime'] = createTime.replace(microsecond=0).isoformat() + ".%03dZ" % (
    createTime.microsecond // 1000)
    heartbeat['origin'] = "%s/%s" % (__program__, os.uname()[1])
    heartbeat['version'] = __version__

    alert_queue.put(json.dumps(heartbeat))


class DynectDaemon(Daemon):

    def run():

        global config, conn, globalconf

        logging.basicConfig(level=logging.INFO,
                            format="%(asctime)s alert-dynect[%(process)d] %(threadName)s %(levelname)s - %(message)s",
                            filename=LOGFILE)
        logging.info('Starting up DynECT GSLB monitor version %s', __version__)

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

        # Initialiase listener
        serv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        serv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        serv.bind((BIND_ADDR))
        serv.listen(5)

        # Start worker threads
        w = WorkerThread()
        w.start()
        logging.info('Starting Worker thread')

        # Start queue threads
        q = QueueThread()
        q.start()
        logging.info('Starting Queue thread')

        while True:
            try:
                # Read (or re-read) config as necessary
                if os.path.getmtime(CONFIGFILE) != config_mod_time:
                    init_config()
                    config_mod_time = os.path.getmtime(CONFIGFILE)

                # Start accept connections
                logging.info('Waiting for incoming connections')
                conn_handler, addr = serv.accept()
                conn.append(conn_handler)
                logging.info('Accept connection from client %s' % str(addr))

            except (KeyboardInterrupt, SystemExit):
                for conn_handler in conn:
                    conn_handler.close()
                w.join()
                q.join()
                os.unlink(PIDFILE)
                logging.info('Graceful exit.')
                sys.exit(0)

import os
import time
import threading
import json
import urllib
import urllib2

import yaml

from alerta.common import config, severity_code
from alerta.common import log as logging
from alerta.common.daemon import Daemon
from alerta.alert import Heartbeat
from alerta.common.mq import Messaging, MessageHandler

Version = '2.0.0'

LOG = logging.getLogger(__name__)
CONF = config.CONF

# AQL constancs
USERNAME = ''
PASSWORD = ''
API_URL = 'http://gw.aql.com/sms/sms_gw.php'

#AQL API Responses
status = {
    '0': 'SMS successfully queued',
    '1': 'SMS queued partially',
    '2': 'Authentication error',
    '3': 'Destination number(s) error',
    '4': 'Send time error',
    '5': 'Insufficient credit or invalid number of msg/destination',
    '9': 'Undefined error',
}

# Global dicts
owners = dict()
hold = dict()
alert = dict()
tokens = dict()

_TokenThread = None            # Worker thread object
_NotifyThread = None
_Lock = threading.Lock()       # Synchronization lock
TOKEN_LIMIT = 10
_token_rate = 60               # Add a token every 60 seconds
INITIAL_TOKENS = 5


class NotifyMessage(MessageHandler):

    def __init__(self, mq):
        self.mq = mq
        MessageHandler.__init__(self)

    def on_message(self, headers, body):
        global alert, hold

        LOG.debug("Received: %s", body)

        alertid = json.loads(body)['id']

        alert[alertid] = json.loads(body)

        LOG.info('%s : [%s] %s', alert[alertid]['lastReceiveId'], alert[alertid]['status'],
                 alert[alertid]['summary'])

        if not should_we_notify(alertid):
            LOG.debug('%s : NOT PAGING for [%s] %s', alert[alertid]['lastReceiveId'], alert[alertid]['status'],
                      alert[alertid]['summary'])
            del alert[alertid]
            return

        if alertid in hold:
            if alert[alertid]['severity'] == severity_code.NORMAL:
                LOG.info('%s : Dropping NORMAL alert %s', alert[alertid]['lastReceiveId'], alertid)
                del hold[alertid]
                del alert[alertid]
            else:
                LOG.info('%s : Update alert %s details', alert[alertid]['lastReceiveId'], alertid)
        else:
            hold[alertid] = time.time() + CONF.notify_wait
            LOG.info('%s : Holding onto alert %s for %s seconds', alert[alertid]['lastReceiveId'], alertid,
                     CONF.notify_wait)

    def on_disconnected(self):
        self.mq.reconnect()


class NotifyDaemon(Daemon):

    def run(self):

        self.running = True

        # Initialiase alert config
        init_config()
        #config_mod_time = os.path.getmtime(CONFIGFILE)  # FIXME

        # Start token bucket thread
        _TokenThread = TokenTopUp()
        _TokenThread.start()

        # Start notify thread
        _NotifyThread = ReleaseThread()
        _NotifyThread.start()

        # Connect to message queue
        self.mq = Messaging()
        self.mq.connect(callback=NotifyMessage(self.mq))
        self.mq.subscribe(destination=CONF.outbound_queue)

        while not self.shuttingdown:
            try:
                # Read (or re-read) config as necessary
                if os.path.getmtime(CONF.yaml_config) != config_mod_time:
                    init_config()
                    config_mod_time = os.path.getmtime(CONF.yaml_config)

                LOG.debug('Waiting for email messages...')
                time.sleep(CONF.loop_every)

                LOG.debug('Send heartbeat...')
                heartbeat = Heartbeat(version=Version)
                self.mq.send(heartbeat)

            except (KeyboardInterrupt, SystemExit):
                self.shuttingdown = True

        _TokenThread.shutdown()
        _NotifyThread.shutdown()

        LOG.info('Shutdown request received...')
        self.running = False

        LOG.info('Disconnecting from message broker...')
        self.mq.disconnect()


def should_we_notify(alertid):
    for tag in alert[alertid]['tags']:
        if tag.startswith('sms:') or tag.startswith('email:'):
            return 1

    return 0


def who_to_notify(tag):
    owner = tag.split(':')[1]
    LOG.info('Identifing owner as %s', owner)
    return owner


def sms_notify(alertid, username, password, destination, url=API_URL):
    message = alert[alertid]['summary']

    data = urllib.urlencode(
        {'username': username, 'password': password, 'destination': destination, 'message': message})

    LOG.info('Api call %s', url + '?' + data)

    req = urllib2.Request(url, data)
    f = urllib2.urlopen(req)
    response = f.read()
    f.close()

    #response = '0:1 SMS successfully queued'
    #response = '2:0 Authentication error'

    # Api call response syntax.
    # <status no>:<no of credits used> <description>
    LOG.info('Api response %s', response)

    # Verify response
    if status['0'] in response:
        return 0
    else:
        return


def init_tokens():
    global tokens

    try:
        for owner in owners:
            tokens[owner, 'sms'] = INITIAL_TOKENS
            tokens[owner, 'email'] = INITIAL_TOKENS

    except Exception, e:
        LOG.error('Failed to initialize tokens %s', e)
        pass


def init_config():
    global owners, USERNAME, PASSWORD

    LOG.info('Loading config.')

    try:
        config = yaml.load(open(CONF.yaml_config))
    except Exception, e:
        LOG.error('Failed to load alert config: %s', e)
        pass

    USERNAME = config['global']['USERNAME']
    PASSWORD = config['global']['PASSWORD']
    owners = config['owners']

    LOG.info('Loaded %d owners in config.', len(owners))

    init_tokens()


def send_notify(alertid):
    global tokens, hold

    try:
        for tag in alert[alertid]['tags']:

            if tag.startswith('sms:') or tag.startswith('email:'):
                who = who_to_notify(tag)
                message = alert[alertid]['summary']

                if tag.startswith('sms:') and tokens[who, 'sms'] > 0:
                    _Lock.acquire()
                    tokens[who, 'sms'] -= 1
                    _Lock.release()
                    LOG.debug('Taken a sms token from %s, there are only %d left', who, tokens[who, 'sms'])
                    sms_notify(alertid, USERNAME, PASSWORD, owners[who]['mobile'])
                elif tokens[who, 'sms'] == 0:
                    LOG.error('%s run out of sms tokens. Failed to notify %s.', who,
                              alert[alertid]['lastReceiveId'])

                if tag.startswith('email:') and tokens[who, 'email'] > 0:
                    _Lock.acquire()
                    tokens[who, 'email'] -= 1
                    _Lock.release()
                    LOG.debug('Taken a email token from %s, there are only %d left', who, tokens[who, 'sms'])
                    email_notify(alertid, owners[who]['email'])
                elif tokens[who, 'email'] == 0:
                    LOG.error('%s run out of email tokens. Failed to notify %s.', who,
                              alert[alertid]['lastReceiveId'])

    except Exception, e:
        LOG.error('Notify sending failed for "%s" - %s - %s', alert[alertid]['lastReceiveId'], message, e)
        pass


    def on_disconnected(self):
        global conn

        LOG.warning('Connection lost. Attempting auto-reconnect to %s', NOTIFY_TOPIC)
        conn.start()
        conn.connect(wait=True)
        conn.subscribe(destination=NOTIFY_TOPIC, ack='auto', headers={'selector': "repeat = 'false'"})


class ReleaseThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.running = False
        self.shuttingdown = False

    def shutdown(self):
        self.shuttingdown = True
        if not self.running:
            return
        self.join()

    def run(self):
        global alert, hold
        self.running = True

        while not self.shuttingdown:
            if self.shuttingdown:
                break

            notified = dict()
            for alertid in hold:
                if hold[alertid] < time.time():
                    LOG.warning('Hold expired for %s and trigger notification', alertid)
                    send_notify(alertid)
                    notified[alertid] = 1

            for alertid in notified:
                del alert[alertid]
                del hold[alertid]

            if not self.shuttingdown:
                time.sleep(5)

        self.running = False


class TokenTopUp(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.running = False
        self.shuttingdown = False

    def shutdown(self):
        self.shuttingdown = True
        if not self.running:
            return
        self.join()

    def run(self):
        global tokens, _token_rate
        self.running = True
        i = 0

        while not self.shuttingdown:
            if self.shuttingdown:
                break

            if i == 6:
                try:
                    i = 0
                    for owner in owners:
                        if tokens[owner, 'sms'] < TOKEN_LIMIT:
                            _Lock.acquire()
                            tokens[owner, 'sms'] += 1
                            _Lock.release()

                        if tokens[owner, 'email'] < TOKEN_LIMIT:
                            _Lock.acquire()
                            tokens[owner, 'email'] += 1
                            _Lock.release()
                except OSError:
                    pass

            if not self.shuttingdown:
                time.sleep(_token_rate / 6)
                i += 1

        self.running = False

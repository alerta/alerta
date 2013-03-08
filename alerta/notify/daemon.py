import os
import sys
import time
import threading
import json
import urllib
import urllib2
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import smtplib
import datetime
import uuid

import yaml
import pytz

from alerta.common import config
from alerta.common import log as logging
from alerta.common.daemon import Daemon
from alerta.alert import Alert, Heartbeat
from alerta.alert import syslog
from alerta.common.mq import Messaging

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


class NotifyMessage(Daemon):

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
            if alert[alertid]['severity'] == 'NORMAL':
                LOG.info('%s : Dropping NORMAL alert %s', alert[alertid]['lastReceiveId'], alertid)
                del hold[alertid]
                del alert[alertid]
            else:
                LOG.info('%s : Update alert %s details', alert[alertid]['lastReceiveId'], alertid)
        else:
            hold[alertid] = time.time() + CONF.notify_wait
            LOG.info('%s : Holding onto alert %s for %s seconds', alert[alertid]['lastReceiveId'], alertid,
                         CONF.notify_wait)


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
        self.mq.connect(callback=NotifyMessage())
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


def email_notify(alertid, email):
    MAILING_LIST = email

    createTime = datetime.datetime.strptime(alert[alertid]['createTime'], '%Y-%m-%dT%H:%M:%S.%fZ')
    createTime = createTime.replace(tzinfo=pytz.utc)
    tz = pytz.timezone(CONF.timezone)
    localTime = createTime.astimezone(tz)

    text = ''
    text += '[%s] %s\n' % (alert[alertid]['status'], alert[alertid]['summary'])
    text += 'Alert Details\n'
    text += 'Alert ID: %s\n' % (alert[alertid]['id'])
    text += 'Create Time: %s\n' % (localTime.strftime('%Y/%m/%d %H:%M:%S'))
    text += 'Resource: %s\n' % (alert[alertid]['resource'])
    text += 'Environment: %s\n' % (','.join(alert[alertid]['environment']))
    text += 'Service: %s\n' % (','.join(alert[alertid]['service']))
    text += 'Event Name: %s\n' % (alert[alertid]['event'])
    text += 'Event Group: %s\n' % (alert[alertid]['group'])
    text += 'Event Value: %s\n' % (alert[alertid]['value'])
    text += 'Severity: %s -> %s\n' % (alert[alertid]['previousSeverity'], alert[alertid]['severity'])
    text += 'Status: %s\n' % (alert[alertid]['status'])
    text += 'Text: %s\n' % (alert[alertid]['text'])

    if 'thresholdInfo' in alert[alertid]:
        text += 'Threshold Info: %s\n' % (alert[alertid]['thresholdInfo'])
    if 'duplicateCount' in alert[alertid]:
        text += 'Duplicate Count: %s\n' % (alert[alertid]['duplicateCount'])
    if 'moreInfo' in alert[alertid]:
        text += 'More Info: %s\n' % (alert[alertid]['moreInfo'])
    text += 'Historical Data\n'
    if 'graphs' in alert[alertid]:
        for g in alert[alertid]['graphs']:
            text += '%s\n' % (g)
    text += 'Raw Alert\n'
    text += '%s\n' % (json.dumps(alert[alertid]))
    text += 'Generated by %s on %s at %s\n' % (
    'alert-notify.py', os.uname()[1], datetime.datetime.now().strftime("%a %d %b %H:%M:%S"))

    LOG.debug('Raw Text: %s', text)

    html = '<p><table border="0" cellpadding="0" cellspacing="0" width="100%">\n'  # table used to center email
    html += '<tr><td bgcolor="#ffffff" align="center">\n'
    html += '<table border="0" cellpadding="0" cellspacing="0" width="700">\n'     # table used to set width of email
    html += '<tr><td bgcolor="#425470"><p align="center" style="font-size:24px;color:#d9fffd;font-weight:bold;"><strong>[%s] %s</strong></p>\n' % (
    alert[alertid]['status'], alert[alertid]['summary'])
    html += '<tr><td><p align="left" style="font-size:18px;line-height:22px;color:#c25130;font-weight:bold;">Alert Details</p>\n'
    html += '<table>\n'
    html += '<tr><td><b>Alert ID:</b></td><td><a href="%s/alerta/details.php?id=%s" target="_blank">%s</a></td></tr>\n' % (
    API_SERVER, alert[alertid]['id'], alert[alertid]['id'])
    html += '<tr><td><b>Create Time:</b></td><td>%s</td></tr>\n' % (localTime.strftime('%Y/%m/%d %H:%M:%S'))
    html += '<tr><td><b>Resource:</b></td><td>%s</td></tr>\n' % (alert[alertid]['resource'])
    html += '<tr><td><b>Environment:</b></td><td>%s</td></tr>\n' % (','.join(alert[alertid]['environment']))
    html += '<tr><td><b>Service:</b></td><td>%s</td></tr>\n' % (','.join(alert[alertid]['service']))
    html += '<tr><td><b>Event Name:</b></td><td>%s</td></tr>\n' % (alert[alertid]['event'])
    html += '<tr><td><b>Event Group:</b></td><td>%s</td></tr>\n' % (alert[alertid]['group'])
    html += '<tr><td><b>Event Value:</b></td><td>%s</td></tr>\n' % (alert[alertid]['value'])
    html += '<tr><td><b>Severity:</b></td><td>%s -> %s</td></tr>\n' % (
    alert[alertid]['previousSeverity'], alert[alertid]['severity'])
    html += '<tr><td><b>Status:</b></td><td>%s</td></tr>\n' % (alert[alertid]['status'])
    html += '<tr><td><b>Text:</b></td><td>%s</td></tr>\n' % (alert[alertid]['text'])
    if 'thresholdInfo' in alert[alertid]:
        html += '<tr><td><b>Threshold Info:</b></td><td>%s</td></tr>\n' % (alert[alertid]['thresholdInfo'])
    if 'duplicateCount' in alert[alertid]:
        html += '<tr><td><b>Duplicate Count:</b></td><td>%s</td></tr>\n' % (alert[alertid]['duplicateCount'])
    if 'moreInfo' in alert[alertid]:
        html += '<tr><td><b>More Info:</b></td><td><a href="%s">ganglia</a></td></tr>\n' % (alert[alertid]['moreInfo'])
    html += '</table>\n'
    html += '</td></tr>\n'
    html += '<tr><td><p align="left" style="font-size:18px;line-height:22px;color:#c25130;font-weight:bold;">Historical Data</p>\n'
    if 'graphs' in alert[alertid]:
        graph_cid = dict()
        for g in alert[alertid]['graphs']:
            graph_cid[g] = str(uuid.uuid4())
            html += '<tr><td><img src="cid:' + graph_cid[g] + '"></td></tr>\n'
    html += '<tr><td><p align="left" style="font-size:18px;line-height:22px;color:#c25130;font-weight:bold;">Raw Alert</p>\n'
    html += '<tr><td><p align="left" style="font-family: \'Courier New\', Courier, monospace">%s</p></td></tr>\n' % (
    json.dumps(alert[alertid]))
    html += '<tr><td>Generated by %s on %s at %s</td></tr>\n' % (
    'alert-mailer.py', os.uname()[1], datetime.datetime.now().strftime("%a %d %b %H:%M:%S"))
    html += '</table>'
    html += '</td></tr></table>'
    html += '</td></tr></table>'

    LOG.debug('HTML Text %s', html)

    msg_root = MIMEMultipart('related')
    msg_root['Subject'] = '[%s] %s' % (alert[alertid]['status'], alert[alertid]['summary'])
    msg_root['From'] = ALERTER_MAIL
    msg_root['To'] = MAILING_LIST
    msg_root.preamble = 'This is a multi-part message in MIME format.'

    msg_alt = MIMEMultipart('alternative')
    msg_root.attach(msg_alt)

    msg_text = MIMEText(text, 'plain')
    msg_alt.attach(msg_text)

    msg_html = MIMEText(html, 'html')
    msg_alt.attach(msg_html)

    if 'graphs' in alert[alertid]:
        msg_img = dict()
        for g in alert[alertid]['graphs']:
            try:
                image = urllib2.urlopen(g).read()
                msg_img[g] = MIMEImage(image)
                LOG.debug('graph cid %s', graph_cid[g])
                msg_img[g].add_header('Content-ID', '<' + graph_cid[g] + '>')
                msg_root.attach(msg_img[g])
            except:
                pass

    try:
        LOG.info('%s : Send email to %s', alert[alertid]['lastReceiveId'], MAILING_LIST)
        s = smtplib.SMTP(SMTP_SERVER)
        s.sendmail(ALERTER_MAIL, MAILING_LIST, msg_root.as_string())
        s.quit()
    except smtplib.SMTPException, e:
        LOG.error('%s : Sendmail failed - %s', alert[alertid]['lastReceiveId'], e)


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

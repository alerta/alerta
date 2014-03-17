import json
import time

from functools import wraps
from flask import request, current_app, render_template, abort

from alerta.api.v2 import app, db, mq
from alerta.api.v2.switch import Switch
from alerta.common import config
from alerta.common import log as logging
from alerta.common.alert import Alert
from alerta.common.heartbeat import Heartbeat
from alerta.common import status_code, severity_code
from alerta.common.utils import DateEncoder
from alerta.api.v2.utils import parse_fields, crossdomain


Version = '3.0.0'

LOG = logging.getLogger(__name__)
CONF = config.CONF


# Over-ride jsonify to support Date Encoding
def jsonify(*args, **kwargs):
    return current_app.response_class(json.dumps(dict(*args, **kwargs), cls=DateEncoder,
                                                 indent=None if request.is_xhr else 2), mimetype='application/json')


def jsonp(func):
    """Wraps JSONified output for JSONP requests."""
    @wraps(func)
    def decorated_function(*args, **kwargs):
        callback = request.args.get('callback', False)
        if callback:
            data = str(func(*args, **kwargs).data)
            content = str(callback) + '(' + data + ')'
            mimetype = 'application/javascript'
            return current_app.response_class(content, mimetype=mimetype)
        else:
            return func(*args, **kwargs)
    return decorated_function


@app.route('/test', methods=['OPTIONS', 'PUT', 'POST', 'DELETE', 'GET'])
@crossdomain(origin='*', headers=['Origin', 'X-Requested-With', 'Content-Type', 'Accept'])
@jsonp
def test():

    return jsonify(
        status="ok",
        method=request.method,
        json=request.json,
        data=request.data,
        args=request.args,
        app_root=app.root_path,
    )


@app.route('/', methods=['GET'])
def routes():

    rules = []
    for rule in app.url_map.iter_rules():
        rule.methods = ','.join([r for r in rule.methods if r not in ['OPTIONS', 'HEAD']])
        if rule.endpoint not in ['test','static']:
            rules.append(rule)
    return render_template('index.html', rules=rules)


@app.route('/api/alerts', methods=['GET'])
@jsonp
def get_alerts():

    try:
        query, sort, limit, query_time = parse_fields(request)
    except Exception, e:
        return jsonify(status="error", message=str(e))

    fields = dict()
    fields['history'] = {'$slice': CONF.history_limit}

    if 'status' not in query:
        query['status'] = 'open'

    alerts = db.get_alerts(query=query, fields=fields, sort=sort, limit=limit)
    total = db.get_count(query=query)  # TODO(nsatterl): possible race condition?

    found = 0
    severity_count = dict.fromkeys(severity_code.ALL, 0)
    status_count = dict.fromkeys(status_code.ALL, 0)

    alert_response = list()
    if len(alerts) > 0:

        last_time = None

        for alert in alerts:
            body = alert.get_body()
            found += 1
            severity_count[body['severity']] += 1
            status_count[body['status']] += 1

            if not last_time:
                last_time = body['lastReceiveTime']
            elif body['lastReceiveTime'] > last_time:
                last_time = body['lastReceiveTime']

            alert_response.append(body)

        return jsonify(
            status="ok",
            total=found,
            more=total > limit,
            alerts=alert_response,
            severityCounts=severity_count,
            statusCounts=status_count,
            lastTime=last_time,
            autoRefresh=Switch.get('auto-refresh-allow').is_on(),
        )
    else:
        return jsonify(
            status="error",
            message="not found",
            total=0,
            more=False,
            alerts=[],
            severityCounts=severity_count,
            statusCounts=status_count,
            lastTime=query_time,
            autoRefresh=Switch.get('auto-refresh-allow').is_on()
        )


@app.route('/api/alert', methods=['OPTIONS', 'POST'])
@crossdomain(origin='*', headers=['Origin', 'X-Requested-With', 'Content-Type', 'Accept'])
@jsonp
def create_alert():

    # Create a new alert
    try:
        newAlert = Alert.parse_alert(request.data)
    except ValueError, e:
        return jsonify(status="error", message=str(e))

    LOG.debug('New alert %s', newAlert)
    mq.send(newAlert)

    if newAlert:
        return jsonify(status="ok", id=newAlert.get_id())
    else:
        return jsonify(status="error", message="something went wrong")


@app.route('/api/alert/<alertid>', methods=['OPTIONS', 'GET'])
@crossdomain(origin='*', headers=['Origin', 'X-Requested-With', 'Content-Type', 'Accept'])
@jsonp
def get_alert(alertid):

    alert = db.get_alert(alertid=alertid)

    if alert:
        return jsonify(status="ok", total=1, alert=alert.get_body())
    else:
        return jsonify(status="ok", message="not found", total=0, alert=None)


@app.route('/api/alert/<alertid>/tag', methods=['OPTIONS', 'PUT'])
@crossdomain(origin='*', headers=['Origin', 'X-Requested-With', 'Content-Type', 'Accept'])
@jsonp
def tag_alert(alertid):

    tag = request.json

    if tag:
        response = db.tag_alert(alertid, tag['tag'])
    else:
        return jsonify(status="error", message="no data")

    if response:
        return jsonify(status="ok")
    else:
        return jsonify(status="error", message="error tagging alert")


@app.route('/api/alert/<alertid>/status', methods=['OPTIONS', 'PUT'])
@crossdomain(origin='*', headers=['Origin', 'X-Requested-With', 'Content-Type', 'Accept'])
@jsonp
def modify_status(alertid):

    status = request.json['status']
    text = request.json['text']

    if status:
        modifiedAlert = db.update_status(alertid=alertid, status=status, text=text)

        # Forward alert to notify topic and logger queue
        mq.send(modifiedAlert, CONF.outbound_queue)
        mq.send(modifiedAlert, CONF.outbound_topic)
        LOG.info('%s : Alert forwarded to %s and %s', modifiedAlert.get_id(), CONF.outbound_queue, CONF.outbound_topic)

    else:
        return jsonify(status="error", message="no data")

    if modifiedAlert:
        return jsonify(status="ok")
    else:
        return jsonify(status="error", message="error changing alert status")


@app.route('/api/alert/<alertid>', methods=['OPTIONS', 'DELETE', 'POST'])
@crossdomain(origin='*', headers=['Origin', 'X-Requested-With', 'Content-Type', 'Accept'])
@jsonp
def delete_alert(alertid):

    error = None

    if request.method == 'DELETE' or (request.method == 'POST' and request.json['_method'] == 'delete'):
        response = db.delete_alert(alertid)

        if response:
            return jsonify(status="ok")
        else:
            return jsonify(status="error", message=error)

    else:
        return jsonify(status="error", message="POST request without '_method' override?")


# Return severity and status counts
@app.route('/api/alert/counts', methods=['GET'])
@jsonp
def get_counts():

    try:
        query, _, _, query_time = parse_fields(request)
    except Exception, e:
        return jsonify(response={"status": "error", "message": str(e)})

    found, severity_count, status_count = db.get_counts(query=query)

    return jsonify(
        status="ok",
        total=found,
        more=False,
        severityCounts=severity_count,
        statusCounts=status_count,
        lastTime=query_time,
        autoRefresh=Switch.get('auto-refresh-allow').is_on(),
    )


@app.route('/pagerduty', methods=['POST'])
def pagerduty():

    if not request.json or not 'messages' in request.json:
        abort(400)

    for message in request.json['messages']:

        LOG.debug('%s', json.dumps(message))

        alertid = message['data']['incident']['incident_key']
        html_url = message['data']['incident']['html_url']
        incident_number = message['data']['incident']['incident_number']
        incident_url = '<a href="%s">#%s</a>' % (html_url, incident_number)

        LOG.info('PagerDuty incident #%s webhook for alert %s', incident_number, alertid)

        LOG.error('previous status %s', db.get_alert(alertid=alertid).status)

        if message['type'] == 'incident.trigger':
            status = status_code.OPEN
            user = message['data']['incident']['assigned_to_user']['name']
            text = 'Incident %s assigned to %s' % (incident_url, user)
        elif message['type'] == 'incident.acknowledge':
            status = status_code.ACK
            user = message['data']['incident']['assigned_to_user']['name']
            text = 'Incident %s acknowledged by %s' % (incident_url, user)
        elif message['type'] == 'incident.unacknowledge':
            status = status_code.OPEN
            text = 'Incident %s unacknowledged due to timeout' % incident_url
        elif message['type'] == 'incident.resolve':
            status = status_code.CLOSED
            if message['data']['incident']['resolved_by_user']:
                user = message['data']['incident']['resolved_by_user']['name']
            else:
                user = 'n/a'
            text = 'Incident %s resolved by %s' % (incident_url, user)
        elif message['type'] == 'incident.assign':
            status = status_code.ASSIGN
            user = message['data']['incident']['assigned_to_user']['name']
            text = 'Incident %s manually assigned to %s' % (incident_url, user)
        elif message['type'] == 'incident.escalate':
            status = status_code.OPEN
            user = message['data']['incident']['assigned_to_user']['name']
            text = 'Incident %s escalated to %s' % (incident_url, user)
        elif message['type'] == 'incident.delegate':
            status = status_code.OPEN
            user = message['data']['incident']['assigned_to_user']['name']
            text = 'Incident %s reassigned due to escalation to %s' % (incident_url, user)
        else:
            status = status_code.UNKNOWN
            text = message['type']
            LOG.warn('Unknown PagerDuty message type: %s', message)

        LOG.info('PagerDuty webhook %s change status to %s', message['type'], status)

        pdAlert = db.update_status(alertid=alertid, status=status, text=text)
        db.tag_alert(alertid=alertid, tag='incident=#%s' % incident_number)

        LOG.error('returned status %s', pdAlert.status)
        LOG.error('current status %s', db.get_alert(alertid=alertid).status)

        # Forward alert to notify topic and logger queue
        if pdAlert:
            pdAlert.origin = 'pagerduty/webhook'
            mq.send(pdAlert, CONF.outbound_queue)
            mq.send(pdAlert, CONF.outbound_topic)
            LOG.info('%s : Alert forwarded to %s and %s', pdAlert.get_id(), CONF.outbound_queue, CONF.outbound_topic)

    return jsonify(status="ok")


# Return a list of heartbeats
@app.route('/api/heartbeats', methods=['GET'])
@jsonp
def get_heartbeats():

    heartbeats = db.get_heartbeats()
    return jsonify(application="alerta", time=int(time.time() * 1000), heartbeats=heartbeats)


@app.route('/api/heartbeat', methods=['OPTIONS', 'POST'])
@crossdomain(origin='*', headers=['Origin', 'X-Requested-With', 'Content-Type', 'Accept'])
@jsonp
def create_heartbeat():

    # Create a new heartbeat
    try:
        heartbeat = Heartbeat.parse_heartbeat(request.data)
    except Exception, e:
        return jsonify(status="error", message=str(e))

    LOG.debug('New heartbeat %s', heartbeat)
    mq.send(heartbeat)

    if heartbeat:
        return jsonify(status="ok", id=heartbeat.get_id())
    else:
        return jsonify(status="error", message="something went wrong")

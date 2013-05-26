import json
import time

from functools import wraps
from flask import request, current_app, render_template, send_from_directory

from alerta.api.v2 import app, db, mq
from alerta.api.v2.switch import Switch
from alerta.common import config
from alerta.common import log as logging
from alerta.common.alert import Alert
from alerta.common.heartbeat import Heartbeat
from alerta.common import status_code, severity_code
from alerta.common.utils import DateEncoder
from alerta.api.v2.utils import parse_fields


Version = '2.0.11'

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


@app.route('/test', methods=['POST', 'GET', 'PUT', 'DELETE'])
@jsonp
def test():

    return jsonify(response={
        "status": "ok",
        "method": request.method,
        "json": request.json,
        "data": request.data,
        "args": request.args,
        "app_root": app.root_path,
    })


# Returns a list of alerts
@app.route('/alerta/api/v2/alerts', methods=['GET'])
@jsonp
def get_alerts():

    query, sort, limit, query_time = parse_fields(request)

    alerts = db.get_alerts(query=query, sort=sort, limit=limit)
    total = db.get_count(query=query)  # TODO(nsatterl): possible race condition?

    found = 0
    severity_count = dict.fromkeys(severity_code.ALL, 0)
    status_count = dict.fromkeys(status_code.ALL, 0)

    alert_details = list()
    if len(alerts) > 0:

        last_time = None

        for alert in alerts:
            body = alert.get_body()

            if body['severity'] in request.args.getlist('hide-alert-repeats') and body['repeat']:
                continue

            if not request.args.get('hide-alert-details', False, bool):
                alert_details.append(body)

            if request.args.get('hide-alert-history', False, bool):
                body['history'] = []

            found += 1
            severity_count[body['severity']] += 1
            status_count[body['status']] += 1

            if not last_time:
                last_time = body['lastReceiveTime']
            elif body['lastReceiveTime'] > last_time:
                last_time = body['lastReceiveTime']

        return jsonify(response={
            "alerts": {
                "alertDetails": alert_details,
                "severityCounts": severity_count,
                "statusCounts": status_count,
                "lastTime": last_time,
            },
            "status": "ok",
            "total": found,
            "more": total > limit,
            "autoRefresh": Switch.get('auto-refresh-allow').is_on(),
        })
    else:
        return jsonify(response={
            "alerts": {
                "alertDetails": [],
                "severityCounts": severity_count,
                "statusCounts": status_count,
                "lastTime": query_time,
            },
            "status": "error",
            "error": "not found",
            "total": 0,
            "more": False,
            "autoRefresh": Switch.get('auto-refresh-allow').is_on(),
        })


@app.route('/alerta/api/v2/alerts/alert.json', methods=['POST'])
@jsonp
def create_alert():

    # Create a new alert
    try:
        data = json.loads(request.data)
    except Exception, e:
        return jsonify(response={"status": "error", "message": e})

    newAlert = Alert(
        resource=data.get('resource', None),
        event=data.get('event', None),
        correlate=data.get('correlatedEvents', None),
        group=data.get('group', None),
        value=data.get('value', None),
        severity=severity_code.parse_severity(data.get('severity', None)),
        environment=data.get('environment', None),
        service=data.get('service', None),
        text=data.get('text', None),
        event_type=data.get('type', 'exceptionAlert'),
        tags=data.get('tags', None),
        origin=data.get('origin', None),
        threshold_info=data.get('thresholdInfo', None),
        timeout=data.get('timeout', None),
        alertid=data.get('id', None),
        raw_data=data.get('rawData', None),
        more_info=data.get('moreInfo', None),
        graph_urls=data.get('graphUrls', None),
    )
    LOG.debug('New alert %s', newAlert)
    mq.send(newAlert)

    if newAlert:
        return jsonify(response={"status": "ok", "id": newAlert.get_id()})
    else:
        return jsonify(response={"status": "error", "message": "something went wrong"})


@app.route('/alerta/api/v2/alerts/alert/<alertid>', methods=['GET', 'PUT', 'POST', 'DELETE'])
@jsonp
def modify_alert(alertid):

    error = None

    # Return a single alert
    if request.method == 'GET':
        alert = db.get_alert(alertid=alertid)
        if alert:
            return jsonify(response={"alert": alert.get_body(), "status": "ok", "total": 1})
        else:
            return jsonify(response={"alert": None, "status": "error", "message": "not found", "total": 0})

    # Update a single alert
    elif request.method == 'PUT':
        if request.json:
            modifiedAlert = db.modify_alert(alertid=alertid, update=request.json)
            if 'status' in request.json:
                modifiedAlert = db.update_status(alertid=alertid, status=request.json['status'])

                # Forward alert to notify topic and logger queue
                mq.send(modifiedAlert, CONF.outbound_queue)
                mq.send(modifiedAlert, CONF.outbound_topic)
                LOG.info('%s : Alert forwarded to %s and %s', modifiedAlert.get_id(), CONF.outbound_queue, CONF.outbound_topic)

        else:
            modifiedAlert = None
            error = "no post data"

        if modifiedAlert:
            return jsonify(response={"status": "ok"})
        else:
            return jsonify(response={"status": "error", "message": error})

    # Delete a single alert
    elif request.method == 'DELETE' or (request.method == 'POST' and request.json['_method'] == 'delete'):
        response = db.delete_alert(alertid)

        if response:
            return jsonify(response={"status": "ok"})
        else:
            return jsonify(response={"status": "error", "message": error})

    else:
        return jsonify(response={"status": "error", "message": "POST request without '_method' override?"})


# Tag an alert
@app.route('/alerta/api/v2/alerts/alert/<alertid>/tag', methods=['PUT'])
@jsonp
def tag_alert(alertid):

    tag = request.json

    if tag:
        response = db.tag_alert(alertid, tag['tag'])
    else:
        return jsonify(response={"status": "error", "message": "no data"})

    if response:
        return jsonify(response={"status": "ok"})
    else:
        return jsonify(response={"status": "error", "message": "error tagging alert"})

# Return severity and status counts
@app.route('/alerta/api/v2/alerts/counts', methods=['GET'])
@jsonp
def get_counts():

    query, _, _, query_time = parse_fields(request)
    found, severity_count, status_count = db.get_counts(query=query)

    return jsonify(response={
        "alerts": {
            "alertDetails": [],
            "severityCounts": severity_count,
            "statusCounts": status_count,
            "lastTime": query_time,
        },
        "status": "ok",
        "total": found,
        "more": False,
        "autoRefresh": Switch.get('auto-refresh-allow').is_on(),
    })


# Return a list of resources
@app.route('/alerta/api/v2/resources', methods=['GET'])
@jsonp
def get_resources():

    query, sort, limit, query_time = parse_fields(request)
    resources = db.get_resources(query=query, sort=sort, limit=limit)
    total = db.get_count(query=query)  # TODO(nsatterl): possible race condition?

    found = 0
    resource_details = list()
    if len(resources) > 0:

        last_time = None

        for resource in resources:
            resource_details.append(resource)
            found += 1

            if not last_time:
                last_time = resource['lastReceiveTime']
            elif resource['lastReceiveTime'] > last_time:
                last_time = resource['lastReceiveTime']

        return jsonify(response={
            "resources": {
                "resourceDetails": resource_details,
                "lastTime": last_time,
            },
            "status": "ok",
            "total": found,
            "more": total > limit
        })
    else:
        return jsonify(response={
            "resources": {
                "resourceDetails": list(),
                "lastTime": query_time,
            },
            "status": "error",
            "error": "not found",
            "total": 0,
            "more": False,
        })

@app.route('/alerta/api/v2/resources/resource/<resource>', methods=['POST', 'DELETE'])
@jsonp
def delete_resource(resource):

    error = None

    # Delete a single alert
    if request.method == 'DELETE' or (request.method == 'POST' and request.json['_method'] == 'delete'):
        response = db.delete_resource(resource)

        if response:
            return jsonify(response={"status": "ok"})
        else:
            return jsonify(response={"status": "error", "message": error})

    else:
        return jsonify(response={"status": "error", "message": "POST request without '_method' override?"})

# Return a list of heartbeats
@app.route('/alerta/api/v2/heartbeats', methods=['GET'])
@jsonp
def get_heartbeats():

    heartbeats = db.get_heartbeats()
    return jsonify(application="alerta", time=int(time.time() * 1000), heartbeats=heartbeats)


@app.route('/alerta/api/v2/heartbeats/heartbeat.json', methods=['POST'])
@jsonp
def create_heartbeat():

    # Create a new heartbeat
    try:
        data = json.loads(request.data)
    except Exception, e:
        return jsonify(response={"status": "error", "message": e})

    heartbeat = Heartbeat(
        origin=data.get('origin', None),
        version=data.get('version', None),
        heartbeatid=data.get('id', None),
    )
    LOG.debug('New heartbeat %s', heartbeat)
    mq.send(heartbeat)

    if heartbeat:
        return jsonify(response={"status": "ok", "id": heartbeat.get_id()})
    else:
        return jsonify(response={"status": "error", "message": "something went wrong"})


@app.route('/alerta/widgets/v2/severity')
def severity_widget():

    label = request.args.get('label', 'Alert Severity')

    return render_template('widgets/severity.html', config=CONF, label=label, query=request.query_string)


@app.route('/alerta/widgets/v2/details')
def details_widget():

    label = request.args.get('label', 'Alert Details')

    return render_template('widgets/details.html', config=CONF, label=label, query=request.query_string)


@app.route('/alerta/dashboard/v2/<name>')
def console(name):

    return render_template(name, config=CONF)


# Only use when running API in stand-alone mode during testing
@app.route('/alerta/dashboard/v2/assets/<path:filename>')
def assets(filename):

    return send_from_directory(CONF.dashboard_dir, filename)


import datetime
import time

from flask import request, Response, url_for, jsonify, render_template, current_app
from flask_cors import cross_origin

try:
    from alerta import build
except Exception:
    from alerta import dev as build

from alerta.app import db
from alerta.app.models.heartbeat import Heartbeat
from alerta.app.models.alert import Alert
from alerta.app.models.switch import Switch, SwitchState
from alerta.app.auth.utils import permission
from alerta.app.models.metrics import Gauge, Counter, Timer, timer
from alerta.version import __version__

from . import mgmt

switches = [
    Switch('auto-refresh-allow', 'Allow consoles to auto-refresh alerts', SwitchState.ON),
    Switch('sender-api-allow', 'Allow alerts to be submitted via the API', SwitchState.ON)
]
total_alert_gauge = Gauge('alerts', 'total', 'Total alerts', 'Total number of alerts in the database')
# FIXME
test_counter = Counter('alerts', 'count', 'Total counts', 'Total number of alerts in the database')
test_timer = Timer('alerts', 'status', 'Total counts', 'Total number of alerts in the database')

started = time.time() * 1000


@mgmt.route('/management', methods=['OPTIONS', 'GET'])
@cross_origin()
def management():

    endpoints = [
        url_for('mgmt.manifest'),
        url_for('mgmt.properties'),
        url_for('mgmt.switchboard'),
        url_for('mgmt.good_to_go'),
        url_for('mgmt.health_check'),
        url_for('mgmt.status'),
        url_for('mgmt.prometheus_metrics')
    ]
    return render_template('management/index.html', endpoints=endpoints)


@mgmt.route('/management/manifest', methods=['OPTIONS', 'GET'])
@cross_origin()
@permission('read:management')
def manifest():

    manifest = {
        "label": "Alerta",
        "release": __version__,
        "build": build.BUILD_NUMBER,
        "date": build.BUILD_DATE,
        "revision": build.BUILD_VCS_NUMBER,
        "description": "Alerta monitoring system",
        "built-by": build.BUILT_BY,
        "built-on": build.HOSTNAME,
    }

    return  jsonify(alerta=manifest)


@mgmt.route('/management/properties', methods=['OPTIONS', 'GET'])
@cross_origin()
@permission('admin:management')
def properties():

    properties = ''

    for k, v in current_app.__dict__.items():
        properties += '%s: %s\n' % (k, v)

    for k, v in current_app.config.items():
        properties += '%s: %s\n' % (k, v)

    return Response(properties, content_type='text/plain')


@mgmt.route('/management/switchboard', methods=['OPTIONS', 'GET', 'POST'])
@cross_origin()
@permission('admin:management')
def switchboard():

    if request.method == 'POST':
        for switch in Switch.get_all():
            try:
                value = request.form[switch.name]
                switch.set_state(value)
            except KeyError:
                pass

        return render_template('management/switchboard.html', switches=switches)
    else:
        switch = request.args.get('switch', None)
        if switch:
            return render_template('management/switchboard.html',
                                   switches=[Switch.get(switch)])
        else:
            return render_template('management/switchboard.html', switches=switches)


@mgmt.route('/management/gtg', methods=['OPTIONS', 'GET'])
@cross_origin()
def good_to_go():

    if db.is_alive:
        return 'OK'
    else:
        return 'FAILED', 503


@mgmt.route('/management/healthcheck', methods=['OPTIONS', 'GET'])
@cross_origin()
def health_check():

    try:
        heartbeats = Heartbeat.find_all()
        for heartbeat in heartbeats:
            delta = datetime.datetime.utcnow() - heartbeat.receive_time
            threshold = int(heartbeat.timeout) * 4
            if delta.seconds > threshold:
                return 'HEARTBEAT_STALE: %s' % heartbeat.origin, 503

    except Exception as e:
        return 'HEALTH_CHECK_FAILED: %s' % e, 503

    return 'OK'


@mgmt.route('/management/status', methods=['OPTIONS', 'GET'])
@cross_origin()
@permission('read:management')
@timer(test_timer) # FIXME
def status():

    test_counter.inc(5)

    now = int(time.time() * 1000)
    total_alert_gauge.set(Alert.get_count())

    metrics = Gauge.find_all()
    metrics.extend(Counter.find_all())
    metrics.extend(Timer.find_all())

    # FIXME
    # auto_refresh_allow = {
    #     "group": "switch",
    #     "name": "auto_refresh_allow",
    #     "type": "text",
    #     "title": "Alert console auto-refresh",
    #     "description": "Allows auto-refresh of alert consoles to be turned off remotely",
    #     "value": "ON" if Switch.get('auto-refresh-allow').is_on() else "OFF",
    # }
    # metrics.append(auto_refresh_allow)

    return jsonify(application="alerta", version=__version__, time=now, uptime=int(now - started),
                   metrics=[metric.serialize for metric in metrics])


@mgmt.route('/management/metrics', methods=['OPTIONS', 'GET'])
@cross_origin()
# @permission('read:management')  # FIXME - prometheus only supports Authorization header with "Bearer" token
def prometheus_metrics():

    total_alert_gauge.set(Alert.get_count())

    output = Gauge.get_gauges(format='prometheus')
    output += Counter.get_counters(format='prometheus')
    output += Timer.get_timers(format='prometheus')

    return Response(output, content_type='text/plain; version=0.0.4; charset=utf-8')

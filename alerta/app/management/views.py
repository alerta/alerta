
import time
import datetime
import logging

from flask import request, Response, url_for, jsonify, render_template

from alerta.app import app, db
from alerta.app.switch import Switch, SwitchState
from alerta.app.utils import crossdomain
from alerta.app.metrics import Gauge, Counter, Timer
from alerta import build

LOG = logging.getLogger(__name__)

import pkg_resources  # part of setuptools
__version__ = pkg_resources.require("alerta")[0].version

switches = [
    Switch('auto-refresh-allow', 'Allow consoles to auto-refresh alerts', SwitchState.ON),
#    Switch('console-api-allow', 'Allow consoles to use the alert API', SwitchState.ON),    # TODO(nsatterl)
#    Switch('sender-api-allow', 'Allow alerts to be submitted via the API', SwitchState.ON),  # TODO(nsatterl)
]
total_alert_gauge = Gauge('alerts', 'total', 'Total alerts', 'Total number of alerts in the database')
started = time.time() * 1000

@app.route('/management', methods=['OPTIONS', 'GET'])
@crossdomain(origin='*', headers=['Origin', 'X-Requested-With', 'Content-Type', 'Accept', 'Authorization'])
def management():

    endpoints = [
        url_for('manifest'),
        url_for('properties'),
        url_for('switchboard'),
        url_for('health_check'),
        url_for('status')
    ]
    return render_template('management/index.html', endpoints=endpoints)


@app.route('/management/manifest', methods=['OPTIONS', 'GET'])
@crossdomain(origin='*', headers=['Origin', 'X-Requested-With', 'Content-Type', 'Accept', 'Authorization'])
def manifest():

    manifest = {
        "label": "Alerta",
        "release": __version__,
        "build": build.BUILD_NUMBER,
        "date": build.BUILD_DATE,
        "revision": build.BUILD_VCS_NUMBER,
        "description": "The Guardian's Alerta monitoring system",
        "built-by": build.BUILT_BY,
        "built-on": build.HOSTNAME,
    }

    return  jsonify(alerta=manifest)


@app.route('/management/properties', methods=['OPTIONS', 'GET'])
@crossdomain(origin='*', headers=['Origin', 'X-Requested-With', 'Content-Type', 'Accept', 'Authorization'])
def properties():

    properties = ''

    for k, v in app.__dict__.items():
        properties += '%s: %s\n' % (k, v)

    for k, v in app.config.items():
        properties += '%s: %s\n' % (k, v)

    return Response(properties, content_type='text/plain')


@app.route('/management/switchboard', methods=['OPTIONS', 'GET', 'POST'])
@crossdomain(origin='*', headers=['Origin', 'X-Requested-With', 'Content-Type', 'Accept', 'Authorization'])
def switchboard():

    if request.method == 'POST':
        for switch in Switch.get_all():
            try:
                value = request.form[switch.name]
                switch.set_state(value)
                LOG.warning('Switch %s set to %s', switch.name, value)
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


@app.route('/management/healthcheck', methods=['OPTIONS', 'GET'])
@crossdomain(origin='*', headers=['Origin', 'X-Requested-With', 'Content-Type', 'Accept', 'Authorization'])
def health_check():

    try:
        if not db.conn.alive():
            return 'NO_DATABASE', 503

        heartbeats = db.get_heartbeats()
        for heartbeat in heartbeats:
            delta = datetime.datetime.utcnow() - heartbeat.receive_time
            threshold = float(heartbeat.timeout) * 4
            if delta.seconds > threshold:
                return 'HEARTBEAT_STALE', 503

    except Exception as e:
        return 'HEALTH_CHECK_FAILED: %s' % e, 503

    return 'OK'


@app.route('/management/status', methods=['OPTIONS', 'GET'])
@crossdomain(origin='*', headers=['Origin', 'X-Requested-With', 'Content-Type', 'Accept', 'Authorization'])
def status():

    total_alert_gauge.set(db.get_count())

    metrics = Gauge.get_gauges()
    metrics.extend(Counter.get_counters())
    metrics.extend(Timer.get_timers())

    auto_refresh_allow = {
        "group": "switch",
        "name": "auto_refresh_allow",
        "type": "text",
        "title": "Alert console auto-refresh",
        "description": "Allows auto-refresh of alert consoles to be turned off remotely",
        "value": "ON" if Switch.get('auto-refresh-allow').is_on() else "OFF",
    }
    metrics.append(auto_refresh_allow)

    now = int(time.time() * 1000)

    return jsonify(application="alerta", version=__version__, time=now, uptime=int(now - started), metrics=metrics)

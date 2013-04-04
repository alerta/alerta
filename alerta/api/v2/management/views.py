
import time

from flask import request, Response, url_for, jsonify, render_template
from alerta.api.v2 import app, db, create_mq
from alerta.api.v2 import switches

from alerta import get_version
from alerta.common import log as logging

LOG = logging.getLogger(__name__)


@app.route('/alerta/management')
def management():

    endpoints = [
        url_for('manifest'),
        url_for('properties'),
        url_for('switchboard'),
        url_for('health_check'),
        url_for('status')
    ]
    return render_template('management/index.html', endpoints=endpoints)


@app.route('/alerta/management/manifest')
def manifest():

    manifest = {
        "label": "Alerta",
        "release": get_version(),
        "build": "",
        "date": "",
        "revision": "",
        "description": "The Guardian's Alerta monitoring system",
        "built-by": "rpmbuild",
        "built-on": "el6gen01.gudev.gnl",
    }

    return  jsonify(alerta=manifest)


@app.route('/alerta/management/properties')
def properties():

    properties = ''

    for k, v in app.__dict__.items():
        properties += '%s: %s\n' % (k, v)

    for k, v in app.config.items():
        properties += '%s: %s\n' % (k, v)

    return Response(properties, content_type='text/plain')


@app.route('/alerta/management/switchboard', methods=['GET', 'POST'])
def switchboard():

    if request.method == 'POST':
        for switch in switches.ALL:
            try:
                value = request.form[switch]
                if value == 'ON':
                    switches.SWITCH_STATUS[switch] = True
                elif value == 'OFF':
                    switches.SWITCH_STATUS[switch] = False
            except KeyError:
                pass

        LOG.warning('auto-refresh-allow=%s, console-api-allow=%s, sender-api-allow=%s',
                    switches.SWITCH_STATUS[switches.AUTO_REFRESH_ALLOW],
                    switches.SWITCH_STATUS[switches.CONSOLE_API_ALLOW],
                    switches.SWITCH_STATUS[switches.SENDER_API_ALLOW])

        return render_template('management/switchboard.html',
                               switches=switches.SWITCH_STATUS,
                               descriptions=switches.SWITCH_DESCRIPTIONS)

    else:
        switch = request.args.get('switch', None)
        if switch:
            return render_template('management/switchboard.html',
                                   switches={switch: switches.SWITCH_STATUS[switch]},
                                   descriptions=switches.SWITCH_DESCRIPTIONS)
        else:
            return render_template('management/switchboard.html',
                                   switches=switches.SWITCH_STATUS,
                                   descriptions=switches.SWITCH_DESCRIPTIONS)


@app.route('/alerta/management/healthcheck')
def health_check():

    try:
        if not create_mq.is_connected():
            return 'NO_MESSAGE_QUEUE', 503

        if not db.conn.alive():
            return 'NO_DATABASE', 503
    except Exception:
        return 'HEALTH_CHECK_FAILED', 503

    return 'OK'


@app.route('/alerta/management/status')
def status():

    metrics = db.get_metrics()

    auto_refresh_allow = {
        "group": "switch",
        "name": "auto_refresh_allow",
        "type": "text",
        "title": "Alert console auto-refresh",
        "description": "Allows auto-refresh of alert consoles to be turned off remotely",
        "value": "ON" if switches.SWITCH_STATUS[switches.AUTO_REFRESH_ALLOW] else "OFF",
    }
    metrics.append(auto_refresh_allow)

    return jsonify(application="alerta", time=int(time.time() * 1000), metrics=metrics)

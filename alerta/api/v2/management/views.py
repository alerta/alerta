
import time

from flask import Response, url_for, jsonify, render_template
from alerta.api.v2 import app, db, create_mq

from alerta import get_version


@app.route('/alerta/management')
def management():

    endpoints = [
        url_for('manifest'),
        url_for('properties'),
        url_for('switchboard'),
        url_for('health_check'),
        url_for('status')
    ]
    return render_template('mgmt.html', endpoints=endpoints)


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


@app.route('/alerta/management/switchboard')
def switchboard():

    return 'NOT_IMPLEMENTED', 404


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
    return jsonify(application="alerta", time=int(time.time() * 1000), metrics=metrics)

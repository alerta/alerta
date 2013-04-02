
from flask import url_for, render_template
from alerta.api.v2 import app, db, create_mq


@app.route('/alerta/management')
def management():

    endpoints = [
        url_for('manifest'),
        url_for('properties'),
        url_for('switchboard'),
        url_for('healthcheck'),
        url_for('status')
    ]
    return render_template('mgmt.html', endpoints=endpoints)


@app.route('/alerta/management/manifest')
def manifest():

    return 'manifestly unjust'


@app.route('/alerta/management/properties')
def properties():

    return 'properties go here'


@app.route('/alerta/management/switchboard')
def switchboard():

    return 'switch bits on/off'


@app.route('/alerta/management/healthcheck')
def healthcheck():

    try:
        if not create_mq.is_connected():
            return 'NO_MESSAGE_QUEUE', 503

        if not db.conn.alive():
            return 'NO_DATABASE', 503

    except Exception, e:
        return e, 501

    return 'OK'


@app.route('/alerta/management/status')
def status():

    return "management status output!"

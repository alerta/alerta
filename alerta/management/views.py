import datetime
import os
import time

from flask import (Response, current_app, g, jsonify, render_template, request,
                   url_for)
from flask_cors import cross_origin

from alerta.app import db
from alerta.auth.decorators import permission
from alerta.exceptions import ApiError, RejectException
from alerta.models.alert import Alert
from alerta.models.enums import Scope
from alerta.models.heartbeat import Heartbeat
from alerta.models.metrics import Counter, Gauge, Timer
from alerta.models.switch import Switch, SwitchState
from alerta.utils.api import process_action
from alerta.utils.audit import write_audit_trail
from alerta.version import __version__

from . import mgmt

try:
    from alerta import build  # type: ignore
except Exception:
    from alerta import dev as build  # type: ignore


switches = [
    Switch('auto-refresh-allow', 'Alerta console auto-refresh',
           'Allow consoles to auto-refresh alerts', SwitchState.ON),
    Switch('sender-api-allow', 'API alert submission', 'Allow alerts to be submitted via the API', SwitchState.ON)
]
total_alert_gauge = Gauge('alerts', 'total', 'Total alerts', 'Total number of alerts in the database')

started = time.time() * 1000


def version_info():
    if current_app.config['SERVER_VERSION'] == 'full':
        return __version__
    elif current_app.config['SERVER_VERSION'] == 'major':
        return __version__.split('.')[0]
    elif current_app.config['SERVER_VERSION'] == 'off':
        return
    else:
        return __version__


@mgmt.route('/management', methods=['OPTIONS', 'GET'])
@cross_origin()
def management():

    endpoints = [
        url_for('mgmt.manifest'),
        url_for('mgmt.properties'),
        url_for('mgmt.switchboard'),
        url_for('mgmt.good_to_go'),
        url_for('mgmt.health_check'),
        url_for('mgmt.housekeeping'),
        url_for('mgmt.status'),
        url_for('mgmt.prometheus_metrics')
    ]
    return render_template('management/index.html', endpoints=endpoints)


@mgmt.route('/management/manifest', methods=['OPTIONS', 'GET'])
@cross_origin()
@permission(Scope.read_management)
def manifest():

    manifest = {
        'release': version_info(),
        'build': build.BUILD_NUMBER,
        'date': build.BUILD_DATE,
        'revision': build.BUILD_VCS_NUMBER
    }

    return jsonify(manifest)


@mgmt.route('/management/properties', methods=['OPTIONS', 'GET'])
@cross_origin()
@permission(Scope.admin_management)
def properties():

    properties = ''

    for k, v in request.environ.items():
        properties += f'{k}: {v}\n'

    for k, v in os.environ.items():
        properties += f'{k}: {v}\n'

    for k, v in current_app.__dict__.items():
        properties += f'{k}: {v}\n'

    for k, v in current_app.config.items():
        properties += f'{k}: {v}\n'

    return Response(properties, content_type='text/plain')


@mgmt.route('/management/switchboard', methods=['OPTIONS', 'GET', 'POST'])
@cross_origin()
@permission(Scope.admin_management)
def switchboard():

    if request.method == 'POST':
        for switch in Switch.find_all():
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
                                   switches=[Switch.find_by_name(switch)])
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
                return f'HEARTBEAT_STALE: {heartbeat.origin}', 503

    except Exception as e:
        current_app.logger.exception(e)
        return 'HEALTH_CHECK_FAILED: Internal Error!', 503

    return 'OK'


@mgmt.route('/management/housekeeping', methods=['OPTIONS', 'GET', 'POST'])
@cross_origin()
@permission(Scope.admin_management)
def housekeeping():
    expired_threshold_hrs = request.args.get('expired', type=int)
    info_threshold_hrs = request.args.get('info', type=int)

    if expired_threshold_hrs:
        expired_threshold = expired_threshold_hrs * 60 * 60  # convert hours to seconds
    else:
        expired_threshold = current_app.config['DELETE_EXPIRED_AFTER']  # seconds

    if info_threshold_hrs:
        info_threshold = info_threshold_hrs * 60 * 60  # convert hours to seconds
    else:
        info_threshold = current_app.config['DELETE_INFO_AFTER']  # seconds

    has_expired, shelve_timeout, ack_timeout = Alert.housekeeping(expired_threshold, info_threshold)

    errors = []
    for alert in has_expired:
        try:
            # pre actioon
            alert, _, text, timeout = process_action(alert, action='expired', text='', timeout=None)
            # update status
            alert = alert.from_expired(text, timeout)
            # post action
            alert, _, text, timeout = process_action(alert, action='expired', text=text, timeout=timeout, post_action=True)
        except RejectException as e:
            write_audit_trail.send(current_app._get_current_object(), event='alert-expire-rejected', message=alert.text,
                                   user=g.login, customers=g.customers, scopes=g.scopes, resource_id=alert.id, type='alert',
                                   request=request)
            errors.append(str(e))
            continue
        except Exception as e:
            raise ApiError(str(e), 500)

        write_audit_trail.send(current_app._get_current_object(), event='alert-expired', message=text, user=g.login,
                               customers=g.customers, scopes=g.scopes, resource_id=alert.id, type='alert', request=request)

    for alert in shelve_timeout + ack_timeout:
        try:
            # pre action
            alert, _, text, timeout = process_action(alert, action='timeout', text='', timeout=None)
            # update status
            alert = alert.from_timeout(text, timeout)
            # post action
            alert, _, text, timeout = process_action(alert, action='timeout', text=text, timeout=timeout, post_action=True)
        except RejectException as e:
            write_audit_trail.send(current_app._get_current_object(), event='alert-timeout-rejected', message=alert.text,
                                   user=g.login, customers=g.customers, scopes=g.scopes, resource_id=alert.id, type='alert',
                                   request=request)
            errors.append(str(e))
            continue
        except Exception as e:
            raise ApiError(str(e), 500)

        write_audit_trail.send(current_app._get_current_object(), event='alert-timeout', message=text, user=g.login,
                               customers=g.customers, scopes=g.scopes, resource_id=alert.id, type='alert', request=request)

    if errors:
        raise ApiError('housekeeping failed', 500, errors=errors)
    else:
        return jsonify(
            status='ok',
            expired=[a.id for a in has_expired],
            unshelve=[a.id for a in shelve_timeout],
            unack=[a.id for a in ack_timeout],
            count=len(has_expired) + len(shelve_timeout) + len(ack_timeout)
        )


@mgmt.route('/management/status', methods=['OPTIONS', 'GET'])
@cross_origin()
@permission(Scope.read_management)
def status():

    now = int(time.time() * 1000)
    total_alert_gauge.set(Alert.get_count())

    metrics = Gauge.find_all()
    metrics.extend(Counter.find_all())
    metrics.extend(Timer.find_all())
    metrics.extend(Switch.find_all())

    return jsonify(application='alerta', version=version_info(), time=now, uptime=int(now - started),
                   metrics=[metric.serialize() for metric in metrics])


@mgmt.route('/management/metrics', methods=['OPTIONS', 'GET'])
@cross_origin()
@permission(Scope.read_management)
def prometheus_metrics():

    now = int(time.time() * 1000)
    total_alert_gauge.set(Alert.get_count())

    metrics = Gauge.find_all()
    metrics += Counter.find_all()
    metrics += Timer.find_all()

    output = [metric.serialize(format='prometheus') for metric in metrics]
    output += (
        '# HELP alerta_uptime_msecs milliseconds since app has started\n'
        '# TYPE alerta_uptime_msecs counter\n'
        'alerta_uptime_msecs {uptime}\n'.format(
            uptime=int(now - started)
        )
    )

    return Response(
        output, content_type='text/plain; version=0.0.4; charset=utf-8'
    )

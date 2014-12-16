from flask import request

from alerta.app import app, db
from alerta.app.utils import jsonify, jsonp, crossdomain, parse_notification
from alerta.app.metrics import Timer
from alerta.plugins import load_plugins, RejectException

LOG = app.logger

@app.before_first_request
def setup():
    global plugins
    plugins = load_plugins()


webhooks_timer = Timer('alerts', 'queries', 'Alert queries', 'Total time to process number of alert queries')
duplicate_timer = Timer('alerts', 'duplicate', 'Duplicate alerts', 'Total time to process number of duplicate alerts')
correlate_timer = Timer('alerts', 'correlate', 'Correlated alerts', 'Total time to process number of correlated alerts')
create_timer = Timer('alerts', 'create', 'Newly created alerts', 'Total time to process number of new alerts')


@app.route('/webhooks/cloudwatch', methods=['OPTIONS', 'POST'])
@crossdomain(origin='*', headers=['Origin', 'X-Requested-With', 'Content-Type', 'Accept'])
@jsonp
def cloudwatch():

    recv_started = webhooks_timer.start_timer()
    try:
        incomingAlert = parse_notification(request.data)
    except RuntimeError:
        return jsonify(status="error", message="failed to parse cloudwatch notification"), 400
    except ValueError, e:
        webhooks_timer.stop_timer(recv_started)
        return jsonify(status="error", message=str(e)), 400

    if incomingAlert:
        for plugin in plugins:
            try:
                incomingAlert = plugin.pre_receive(incomingAlert)
            except RejectException as e:
                return jsonify(status="error", message=str(e)), 403
            except Exception as e:
                LOG.warning('Error while running pre-receive plug-in: %s', e)
            if not incomingAlert:
                LOG.error('Plug-in pre-receive hook did not return modified alert')

    try:
        if db.is_duplicate(incomingAlert):

            started = duplicate_timer.start_timer()
            alert = db.save_duplicate(incomingAlert)
            duplicate_timer.stop_timer(started)

            for plugin in plugins:
                try:
                    plugin.post_receive(alert)
                except Exception as e:
                    LOG.warning('Error while running post-receive plug-in: %s', e)

        elif db.is_correlated(incomingAlert):

            started = correlate_timer.start_timer()
            alert = db.save_correlated(incomingAlert)
            correlate_timer.stop_timer(started)

            for plugin in plugins:
                try:
                    plugin.post_receive(alert)
                except Exception as e:
                    LOG.warning('Error while running post-receive plug-in: %s', e)

        else:
            started = create_timer.start_timer()
            alert = db.create_alert(incomingAlert)
            create_timer.stop_timer(started)

            for plugin in plugins:
                try:
                    plugin.post_receive(alert)
                except Exception as e:
                    LOG.warning('Error while running post-receive plug-in: %s', e)

        webhooks_timer.stop_timer(recv_started)

    except Exception, e:
        return jsonify(status="error", message=str(e)), 500

    if alert:
        body = alert.get_body()
        body['href'] = "%s/%s" % (request.base_url, alert.id)
        return jsonify(status="ok", id=alert.id, alert=body), 201, {'Location': '%s/%s' % (request.base_url, alert.id)}
    else:
        return jsonify(status="error", message="alert insert or update failed"), 500

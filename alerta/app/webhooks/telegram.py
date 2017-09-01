
from flask import request, jsonify
from flask_cors import cross_origin

from alerta.app.auth.utils import permission
from alerta.app.models.alert import Alert
from alerta.app.models.blackout import Blackout

from . import webhooks


@webhooks.route('/webhooks/telegram', methods=['OPTIONS', 'POST'])
@cross_origin()
@permission('write:webhooks')
def telegram():

    data = request.json
    if 'callback_query' in data:
        command, alert_id = data['callback_query']['data'].split(' ', 1)
        alert = Alert.get(alert_id)
        if not alert:
            jsonify(status="error", message="alert not found for Telegram message")

        if command == '/ack':
            alert.set_status(status='ack', text='status change via Telegram')
        elif command == '/close':
            alert.set_status(status='closed', text='status change via Telegram')
        elif command == '/blackout':
            environment, resource, event = alert.split('|', 2)
            blackout = Blackout(environment, resource=resource, event=event)
            blackout.create()

        return jsonify(status="ok")
    else:
        return jsonify(status="error", message="no callback_query in Telegram message"), 400

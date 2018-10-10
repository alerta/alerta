import json
import logging
from typing import Any, Dict, Tuple

from flask import g, jsonify, request
from flask_cors import cross_origin
from werkzeug.datastructures import ImmutableMultiDict

from alerta.auth.decorators import permission
from alerta.exceptions import ApiError
from alerta.models.alert import Alert
from alerta.utils.response import absolute_url

from . import webhooks

LOG = logging.getLogger(__name__)

JSON = Dict[str, Any]


def parse_slack(data: ImmutableMultiDict) -> Tuple[str, str, str]:
    payload = json.loads(data['payload'])

    user = payload.get('user', {}).get('name')
    alert_id = payload.get('callback_id')
    action = payload.get('actions', [{}])[0].get('value')

    if not alert_id:
        raise ValueError('Alert {} not match'.format(alert_id))
    elif not user:
        raise ValueError('User {} not exist'.format(user))
    elif not action:
        raise ValueError('Non existent action {}'.format(action))

    return alert_id, user, action


def build_slack_response(alert: Alert, action: str, user: str, data: ImmutableMultiDict) -> JSON:
    response = json.loads(data['payload']).get('original_message', {})

    actions = ['watch', 'unwatch']
    message = (
        'User {user} is {action}ing alert {alert}' if action in actions else
        'The status of alert {alert} is {status} now!').format(
            alert=alert.get_id(short=True), status=alert.status.capitalize(),
            action=action, user=user
    )

    attachment_response = {
        'fallback': message, 'pretext': 'Action done!', 'color': '#808080',
        'title': message, 'title_link': absolute_url('/alert/' + alert.id)
    }

    # clear interactive buttons and add new attachment as response of action
    if action not in actions:
        attachments = response.get('attachments', [])
        for attachment in attachments:
            attachment.pop('actions', None)
        attachments.append(attachment_response)
        response['attachments'] = attachments
        return response

    # update the interactive button of all actions
    next_action = actions[(actions.index(action) + 1) % len(actions)]
    for attachment in response.get('attachments', []):
        for attached_action in attachment.get('actions', []):
            if action == attached_action.get('value'):
                attached_action.update({
                    'name': next_action, 'value': next_action,
                    'text': next_action.capitalize()
                })

    return response


@webhooks.route('/webhooks/slack', methods=['OPTIONS', 'POST'])
@cross_origin()
@permission('write:webhooks')
def slack():
    alert_id, user, action = parse_slack(request.form)

    customers = g.get('customers', None)
    alert = Alert.find_by_id(alert_id, customers=customers)
    if not alert:
        jsonify(status='error', message='alert not found for #slack message')

    if action in ['open', 'ack', 'close']:
        alert.set_status(status=action, text='status change via #slack by {}'.format(user))
    elif action in ['watch', 'unwatch']:
        alert.untag(tags=['{}:{}'.format(action, user)])
    else:
        raise ApiError('Unsupported #slack action', 400)

    response = build_slack_response(alert, action, user, request.form)
    return jsonify(**response), 201

import json
from typing import Any, Dict, Tuple

from flask import current_app, g, jsonify, request
from werkzeug.datastructures import ImmutableMultiDict

from alerta.exceptions import ApiError
from alerta.models.alert import Alert
from alerta.utils.audit import write_audit_trail
from alerta.utils.response import absolute_url

from . import WebhookBase

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


class SlackWebhook(WebhookBase):
    """
    Slack apps
    See https://api.slack.com/slack-apps
    """

    def incoming(self, query_string, payload):

        alert_id, user, action = parse_slack(payload)

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

        text = 'alert updated via slack webhook'
        write_audit_trail.send(current_app._get_current_object(), event='webhook-updated', message=text,
                               user=g.login, customers=g.customers, scopes=g.scopes, resource_id=alert.id,
                               type='alert', request=request)

        response = build_slack_response(alert, action, user, payload)
        return jsonify(**response), 201

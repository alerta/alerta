
import logging
import os
from typing import Any, Dict, List  # noqa

from flask import current_app, g, jsonify, request
from flask_cors import cross_origin

from alerta.auth.decorators import permission
from alerta.models.alert import Alert
from alerta.models.blackout import Blackout

from . import webhooks

LOG = logging.getLogger(__name__)

JSON = Dict[str, Any]


def send_message_reply(alert: Alert, action: str, user: str, data: JSON) -> None:
    try:
        import telepot  # type: ignore
    except ImportError as e:
        LOG.warning("You have configured Telegram but 'telepot' client is not installed", exc_info=True)
        return

    try:
        bot_id = os.environ.get('TELEGRAM_TOKEN') or current_app.config.get('TELEGRAM_TOKEN')
        dashboard_url = os.environ.get('DASHBOARD_URL') or current_app.config.get('DASHBOARD_URL')
        chat_id = os.environ.get('TELEGRAM_CHAT_ID') or current_app.config.get('TELEGRAM_CHAT_ID')
        bot = telepot.Bot(bot_id)

        # message info
        message_id = data['callback_query']['message']['message_id']
        message_log = '\n'.join(data['callback_query']['message']['text'].split('\n')[1:])

        # process buttons for reply text
        inline_keyboard, reply = [], 'The status of alert {alert} is *{status}* now!'  # type: List[List[JSON]], str

        actions = ['watch', 'unwatch']
        if action in actions:
            reply = 'User `{user}` is _{status}ing_ alert {alert}'
            next_action = actions[(actions.index(action) + 1) % len(actions)]
            inline_keyboard = [
                [
                    {'text': next_action.capitalize(), 'callback_data': '/{} {}'.format(next_action, alert.id)},
                    {'text': 'Ack', 'callback_data': '{} {}'.format('/ack', alert.id)},
                    {'text': 'Close', 'callback_data': '{} {}'.format('/close', alert.id)}
                ]
            ]

        # format message response
        alert_short_id = alert.get_id(short=True)
        alert_url = '{}/#/alert/{}'.format(dashboard_url, alert.id)
        reply = reply.format(alert=alert_short_id, status=action, user=user)
        message = '{alert} *{level} - {event} on {resouce}*\n{log}\n{reply}'.format(
            alert='[{}]({})'.format(alert_short_id, alert_url), level=alert.severity.capitalize(),
            event=alert.event, resouce=alert.resource, log=message_log, reply=reply)

        # send message
        bot.editMessageText(
            msg_identifier=(chat_id, message_id), text=message,
            parse_mode='Markdown', reply_markup={'inline_keyboard': inline_keyboard}
        )
    except Exception as e:
        LOG.warning('Error sending reply message', exc_info=True)


@webhooks.route('/webhooks/telegram', methods=['OPTIONS', 'POST'])
@cross_origin()
@permission('write:webhooks')
def telegram():

    data = request.json
    if 'callback_query' in data:
        author = data['callback_query']['from']
        user = '{} {}'.format(author.get('first_name'), author.get('last_name'))
        command, alert_id = data['callback_query']['data'].split(' ', 1)

        customers = g.get('customers', None)
        alert = Alert.find_by_id(alert_id, customers=customers)
        if not alert:
            jsonify(status='error', message='alert not found for Telegram message')

        action = command.lstrip('/')
        if action in ['open', 'ack', 'close']:
            alert.set_status(status=action, text='status change via Telegram')
        elif action in ['watch', 'unwatch']:
            alert.untag(tags=['{}:{}'.format(action, user)])
        elif action == 'blackout':
            environment, resource, event = command.split('|', 2)
            blackout = Blackout(environment, resource=resource, event=event)
            blackout.create()

        send_message_reply(alert, action, user, data)
        return jsonify(status='ok')
    else:
        return jsonify(status='ok', message='no callback_query in Telegram message')

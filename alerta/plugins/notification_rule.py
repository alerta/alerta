import logging

from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from alerta.models.notification_rule import NotificationRule, NotificationChannel
from alerta.models.alert import Alert
from alerta.plugins import PluginBase


LOG = logging.getLogger('alerta.plugins.notification_rule')


def get_notification_id(notification_rule: NotificationRule) -> 'str':
    """
    Returns id field of a notification rule
    """
    return notification_rule['id']


def remove_unspeakable_chr(message: str, unspeakables: 'dict[str,str]' = None):
    """
    Removes unspeakable characters from string like _,-,:.
    unspeakables: dictionary with keys as unspeakable charecters and value as replace string
    """
    unspeakable_chrs = {'_': ' ', ' - ': '. ', ' -': '.', '-': ' ', ':': '.'}
    unspeakable_chrs.update(unspeakables or {})
    speakable_message = message
    for unspeakable_chr, replacement_str in unspeakable_chrs.items():
        speakable_message = speakable_message.replace(unspeakable_chr, replacement_str)
    return speakable_message


class NotificationRulesHandler(PluginBase):
    """
    Default notification rules handler for sending messages and making calls
    when a notification rule is active during new alert status
    """

    def get_twilio_client(self, channel: NotificationChannel, **kwargs):
        return Client(channel.api_sid, channel.api_token)

    def make_call(self, message: str, channel: NotificationChannel, receiver: str, **kwargs):
        twiml_message = f'<Response><Pause/><Say>{remove_unspeakable_chr(message)}</Say></Response>'
        call_client = self.get_twilio_client(channel, **kwargs)
        if not call_client:
            return
        self.send_sms(message, channel, receiver, client=call_client)
        return call_client.calls.create(
            twiml=twiml_message,
            to=receiver,
            from_=channel.sender,
        )

    def send_sms(self, message: str, channel: NotificationChannel, receiver: str, client: Client = None, **kwargs):
        sms_client = client or self.get_twilio_client(channel, **kwargs)
        if not sms_client:
            return
        return sms_client.messages.create(body=message, to=receiver, from_=channel.sender)

    def send_email(self, message: str, channel: NotificationChannel, receivers: list, **kwargs):
        newMail = Mail(
            from_email=channel.sender,
            to_emails=receivers,
            subject='Alerta',
            html_content=message,
        )
        email_client = SendGridAPIClient(channel.api_token)
        return email_client.send(newMail)

    def pre_receive(self, alert, **kwargs):
        return alert

    def post_receive(self, alert: 'Alert', **kwargs):

        if alert.repeat:
            return

        standard_message = '%(environment)s: %(severity)s alert for %(service)s - %(resource)s is %(event)s'

        message_objs = alert.serialize.copy()
        for key, val in message_objs.items():
            try:
                value_type = type(val)
                if key != 'history' and key != 'twilioRules' and key != 'notificationRules' and value_type == list:
                    message_objs[key] = ', '.join(val)
                if value_type == str and key == 'severity':
                    message_objs[key] = val.capitalize()
            except Exception as err:
                LOG.error(f'Error while handling message objs: {str(err)}')
                continue
        for notification_rule in alert.get_notification_rules():
            message = (
                notification_rule.text if notification_rule.text != '' and notification_rule.text is not None else standard_message
            ) % message_objs
            channel = notification_rule.channel
            notification_type = channel.type
            if notification_type == 'sendgrid':
                try:
                    self.send_email(message, channel, notification_rule.receivers)
                except Exception as err:
                    LOG.error('NotificationRule: ERROR - %s', str(err))
            elif 'twilio' in notification_type:
                for receiver in notification_rule.receivers:
                    try:
                        if 'call' in notification_type:
                            self.make_call(message, channel, receiver)
                        elif 'sms' in notification_type:
                            self.send_sms(message, channel, receiver)

                    except TwilioRestException as err:
                        LOG.error('TwilioRule: ERROR - %s', str(err))

    def status_change(self, alert, status, text, **kwargs):
        return

    def take_action(self, alert, action, text, **kwargs):
        raise NotImplementedError

    def delete(self, alert, **kwargs) -> bool:
        raise NotImplementedError

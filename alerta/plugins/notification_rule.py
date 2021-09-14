import logging
from alerta.app import db
from threading import Thread

import smtplib

from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from alerta.models.notification_rule import NotificationRule, NotificationChannel
from alerta.models.on_call import OnCall
from alerta.models.user import User
from alerta.models.alert import Alert
from alerta.plugins import PluginBase


LOG = logging.getLogger('alerta.plugins.notification_rule')


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

    def send_smtp_mail(self, message: str, channel: NotificationChannel, receivers: list, on_call_users: 'set[User]', **kwargs):
        mails = set([*receivers, *[user.email for user in on_call_users]])
        server = smtplib.SMTP_SSL(channel.host)
        server.login(channel.api_sid, channel.api_token)
        server.sendmail(channel.sender, list(mails), f"From: {channel.sender}\nTo: {','.join(mails)}\nSubject: Alerta\n\n{message}")
        server.quit()

    def send_email(self, message: str, channel: NotificationChannel, receivers: list, on_call_users: 'set[User]', **kwargs):
        mails = set([*receivers, *[user.email for user in on_call_users]])
        newMail = Mail(
            from_email=channel.sender,
            to_emails=list(mails),
            subject='Alerta',
            html_content=message,
        )
        email_client = SendGridAPIClient(channel.api_token)
        return email_client.send(newMail)

    def get_message_obj(self, alertobj: 'dict[str,any]') -> 'dict[str,any]':
        alertobjcopy = alertobj.copy()
        for objname, objval in alertobj.items():
            try:
                value_type = type(objval)
                if objname != 'history' and objname != 'twilioRules' and objname != 'notificationRules' and objname != 'onCalls' and value_type == list:
                    alertobjcopy[objname] = ', '.join(objval)
                if value_type == str and objname == 'severity':
                    alertobjcopy[objname] = objval.capitalize()
                if value_type == dict:
                    for cmpxobjname, cmpxobjval in objval.items():
                        alertobjcopy[f'{objname}.{cmpxobjname}'] = cmpxobjval
                if value_type == list:
                    for index, value in enumerate(objval):
                        alertobjcopy[f'{objname}[{index}]'] = value
            except Exception as err:
                LOG.error(f'Error while handling message objs: {str(err)}')
                continue

        return alertobjcopy

    def handle_notifications(self, alert: 'Alert', notifications: 'list[list[NotificationRule or NotificationChannel]]', users: 'list[set[User or None]]'):
        standard_message = '%(environment)s: %(severity)s alert for %(service)s - %(resource)s is %(event)s'
        for notification_rule, channel in notifications:
            if channel == None:
                return

            on_users: 'set[User]' = set()
            if notification_rule.use_oncall:
                for user in users:
                    on_users.update(user)

            message = (
                notification_rule.text if notification_rule.text != '' and notification_rule.text is not None else standard_message
            ) % self.get_message_obj(alert.serialize)
            notification_type = channel.type
            if notification_type == 'sendgrid':
                try:
                    self.send_email(message, channel, notification_rule.receivers, on_users)
                except Exception as err:
                    LOG.error('NotificationRule: ERROR - %s', str(err))
            elif notification_type == 'smtp':
                try:
                    self.send_smtp_mail(message, channel, notification_rule.receivers, on_users)
                except Exception as err:
                    LOG.error('NotificationRule: ERROR - %s', str(err))
            elif 'twilio' in notification_type:

                for number in set([*notification_rule.receivers, *[f"{user.country_code}{user.phone_number}" for user in on_users]]):
                    if number == None or number == '':
                        continue
                    try:
                        if 'call' in notification_type:
                            self.make_call(message, channel, number)
                        elif 'sms' in notification_type:
                            self.send_sms(message, channel, number)

                    except TwilioRestException as err:
                        LOG.error('TwilioRule: ERROR - %s', str(err))

    def pre_receive(self, alert, **kwargs):
        return alert

    def post_receive(self, alert: 'Alert', **kwargs):

        if alert.repeat:
            return
        notification_rules = NotificationRule.find_all_active(alert)
        notifications = [[notification_rule, notification_rule.channel] for notification_rule in notification_rules]
        on_users = [on_call.users for on_call in OnCall.find_all_active(alert)]
        Thread(target=self.handle_notifications, args=[alert, notifications, on_users]).start()

    def status_change(self, alert, status, text, **kwargs):
        return

    def take_action(self, alert, action, text, **kwargs):
        raise NotImplementedError

    def delete(self, alert, **kwargs) -> bool:
        raise NotImplementedError

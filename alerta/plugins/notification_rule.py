import logging

from cryptography.fernet import Fernet, InvalidToken
from alerta.app import db
import json
from threading import Thread
import requests
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
TWILIO_MAX_SMS_LENGTH = 1600

LINK_MOBILITY_XML = """
<?xml version="1.0"?>
<SESSION>
  <CLIENT>%(username)s</CLIENT>
  <PW>%(password)s</PW>
  <MSGLST>
    <MSG>
      <TEXT>%(message)s</TEXT>
      <SND>%(sender)s</SND>
      <RCV>{receivers}</RCV>
    </MSG>
  </MSGLST>
</SESSION>
""".split("\n")


def remove_unspeakable_chr(message: str, unspeakables: 'dict[str,str]|None' = None):
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

    def get_twilio_client(self, channel: NotificationChannel, fernet: Fernet, **kwargs):
        try:
            api_sid = fernet.decrypt(channel.api_sid.encode()).decode()
            api_token = fernet.decrypt(channel.api_token.encode()).decode()
        except InvalidToken:
            api_sid = channel.api_sid
            api_token = channel.api_token
        return Client(api_sid, api_token)

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

    def send_sms(self, message: str, channel: NotificationChannel, receiver: str, fernet: Fernet, client: Client = None, **kwargs):
        restricted_message = message[: TWILIO_MAX_SMS_LENGTH - 4]
        body = message if len(message) <= TWILIO_MAX_SMS_LENGTH else restricted_message[: restricted_message.rfind(" ")] + " ..."
        sms_client = client or self.get_twilio_client(channel, fernet, **kwargs)
        if not sms_client:
            return
        return sms_client.messages.create(body=body, to=receiver, from_=channel.sender)

    def send_link_mobility_sms(self, message: str, channel: NotificationChannel, receivers: "list[str]", fernet: Fernet, **kwargs):
        numberOfReceivers = len(receivers)
        if numberOfReceivers == 0:
            return
        headers = {"Content-Type": "application/json"}
        try:
            headers["Authorization"] = f"Basic {fernet.decrypt(channel.api_sid.encode()).decode()}:{fernet.decrypt(channel.api_token.encode()).decode()}"
        except InvalidToken:
            headers["Authorization"] = f"Basic {channel.api_sid}:{channel.api_token}"
        data = json.dumps({"platformId": channel.platform_id, "platformPartnerId": channel.platform_partner_id, "useDeliveryReport": False, "sendRequestMessages": [{"source": channel.sender, "destination": receiver, "userData": message} for receiver in receivers]} if numberOfReceivers > 1 else {"platformId": channel.platform_id, "platformPartnerId": channel.platform_partner_id, "useDeliveryReport": False, "source": channel.sender, "destination": receivers[0], "userData": message})
        LOG.error(data)
        LOG.error(f"{channel.host}/sms/{'send' if numberOfReceivers == 1 else 'sendbatch'}")
        return requests.post(f"{channel.host}/sms/{'send' if numberOfReceivers == 1 else 'sendbatch'}", data, headers=headers, verify=channel.verify if channel.verify == None or channel.verify.lower() != "false" else False)
    
    def send_link_mobility_xml(self, message: str, channel: NotificationChannel, receivers: "list[str]", fernet: Fernet, **kwargs):
        try:
            content = {"message": message, "username": fernet.decrypt(channel.api_sid.encode()).decode(), "sender": channel.sender, "password": fernet.decrypt(channel.api_token.encode()).decode()}
        except InvalidToken:
            content = {"message": message, "username": channel.api_sid, "sender": channel.sender, "password": channel.api_token}
            
        xml_content: "list[str]" = kwargs["xml"]
        for line in xml_content:
            receive_start = line.find("{receivers}")
            if receive_start == -1:
                continue
            _receiver_lines = [line.replace("{receivers}", receiver.replace("+", "")) for receiver in receivers]
            xml_content[xml_content.index(line)] = "".join(_receiver_lines)
        xml_string = "".join(xml_content)
            
        data = xml_string.replace("{", "%(").replace("}", ")s") % content
        
        headers = {"Content-Type": "application/xml"}
        return requests.post(f"{channel.host}", data, headers=headers, verify=channel.verify if channel.verify == None or channel.verify.lower() != "false" else False)

    def send_smtp_mail(self, message: str, channel: NotificationChannel, receivers: list, on_call_users: 'set[User]', fernet: Fernet, **kwargs):
        mails = set([*receivers, *[user.email for user in on_call_users]])
        server = smtplib.SMTP_SSL(channel.host)
        try:
            api_sid = fernet.decrypt(channel.api_sid.encode()).decode()
            api_token = fernet.decrypt(channel.api_token.encode()).decode()
        except InvalidToken:
            api_sid = channel.api_sid
            api_token = channel.api_token
        server.login(api_sid, api_token)
        server.sendmail(channel.sender, list(mails), f"From: {channel.sender}\nTo: {','.join(mails)}\nSubject: Alerta\n\n{message}")
        server.quit()

    def send_email(self, message: str, channel: NotificationChannel, receivers: list, on_call_users: 'set[User]', fernet: Fernet, **kwargs):
        mails = set([*receivers, *[user.email for user in on_call_users]])
        newMail = Mail(
            from_email=channel.sender,
            to_emails=list(mails),
            subject='Alerta',
            html_content=message,
        )
        try:
            api_token = fernet.decrypt(channel.api_token.encode()).decode()
        except InvalidToken:
            api_token = channel.api_token
        email_client = SendGridAPIClient(api_token)
        return email_client.send(newMail)

    def get_message_obj(self, alertobj: 'dict') -> 'dict':
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

    def handle_notifications(self, alert: 'Alert', notifications: 'list[tuple[NotificationRule,NotificationChannel]]', users: 'list[set[User or None]]', fernet: Fernet):
        standard_message = '%(environment)s: %(severity)s alert for %(service)s - %(resource)s is %(event)s'
        for notification_rule, channel in notifications:
            if channel == None:
                return

            on_users: 'set[User]' = set(*users) if notification_rule.use_oncall else set()

            message = (
                notification_rule.text if notification_rule.text != '' and notification_rule.text is not None else standard_message
            ) % self.get_message_obj(alert.serialize)
            notification_type = channel.type
            if notification_type == 'sendgrid':
                try:
                    self.send_email(message, channel, notification_rule.receivers, on_users, fernet)
                except Exception as err:
                    LOG.error('NotificationRule: ERROR - %s', str(err))
            elif notification_type == 'smtp':
                try:
                    self.send_smtp_mail(message, channel, notification_rule.receivers, on_users, fernet)
                except Exception as err:
                    LOG.error('NotificationRule: ERROR - %s', str(err))
            elif 'twilio' in notification_type:

                for number in set([*notification_rule.receivers, *[f"{user.country_code}{user.phone_number}" for user in on_users]]):
                    if number == None or number == '':
                        continue
                    try:
                        if 'call' in notification_type:
                            self.make_call(message, channel, number, fernet)
                        elif 'sms' in notification_type:
                            self.send_sms(message, channel, number, fernet)

                    except TwilioRestException as err:
                        LOG.error('TwilioRule: ERROR - %s', str(err))
            elif notification_type == 'link_mobility':
                self.send_link_mobility_sms(message, channel, list(set([*notification_rule.receivers, *[f"{user.country_code}{user.phone_number}" for user in on_users]])), fernet)
            elif notification_type == 'link_mobility_xml':
                response = self.send_link_mobility_xml(message, channel, list(set([*notification_rule.receivers, *[f"{user.country_code}{user.phone_number}" for user in on_users]])), fernet, xml=LINK_MOBILITY_XML)
                if response.content.decode().find("FAIL") != -1:
                    LOG.error(response.content)
                else:
                    LOG.info(response.content)

    def pre_receive(self, alert, **kwargs):
        return alert

    def post_receive(self, alert: 'Alert', **kwargs):
        config = kwargs.get('config')
        fernet = Fernet(config['NOTIFICATION_KEY'])
        if alert.repeat:
            return
        notification_rules = NotificationRule.find_all_active(alert)
        notifications = [[notification_rule, notification_rule.channel] for notification_rule in notification_rules]
        on_users = [on_call.users for on_call in OnCall.find_all_active(alert)]
        Thread(target=self.handle_notifications, args=[alert, notifications, on_users, fernet]).start()

    def status_change(self, alert, status, text, **kwargs):
        return

    def take_action(self, alert, action, text, **kwargs):
        raise NotImplementedError

    def delete(self, alert, **kwargs) -> bool:
        raise NotImplementedError

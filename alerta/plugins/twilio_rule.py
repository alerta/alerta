import logging

from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from alerta.models.twilio_rule import TwilioRule
from alerta.plugins import PluginBase

LOG = logging.getLogger('alerta.plugins.twilio_rule')


def get_twilio_id(twilio_rule: TwilioRule) -> 'str':
    """
    Returns id field of a twilio rule
    """
    return twilio_rule['id']


def remove_unspeakable_chr(message: str, unspeakables: 'dict[str,str]' = None):
    """
    Removes unspeakable characters from string like _,-,:.
    unspeakables: dictionary with keys as unspeakable charecters and value as replace string
    """
    unspeakable_chrs = {'_': ' ', ' - ': '. ', ' -': '.', '-': ' ', ':': '.'}
    unspeakable_chrs.update(unspeakables or {})
    for unspeakable_chr, replacement_str in unspeakable_chrs.items():
        message = message.replace(unspeakable_chr, replacement_str)
    return message


class TwilioRulesHandler(PluginBase):
    """
    Default twilio rules handler for sending messages and making calls
    when a twilio rule is active during new alert status
    """

    def pre_receive(self, alert, **kwargs):
        return alert

    def post_receive(self, alert: 'Alert', **kwargs):

        twilio_account_sid = self.get_config('TWILIO_ACCOUNT_SID', default='', type=str, **kwargs)
        twilio_auth_token = self.get_config('TWILIO_AUTH_TOKEN', default='', type=str, **kwargs)
        if alert.repeat or twilio_auth_token == '' or twilio_auth_token == '':
            return

        message = '%s: %s alert for %s - %s is %s' % (
            alert.environment,
            alert.severity.capitalize(),
            ','.join(alert.service),
            alert.resource,
            alert.event,
        )

        client = Client(twilio_account_sid, twilio_auth_token)
        for twilio_rule in alert.get_twilio_rules():
            for number in twilio_rule.to_numbers:
                try:
                    if twilio_rule.type == 'call':
                        twiml_message = f'<Response><Pause/><Say>{remove_unspeakable_chr(message)}</Say></Response>'
                        twilio_response = client.calls.create(
                            twiml=twiml_message,
                            to=number,
                            from_=twilio_rule.from_number,
                        )
                    else:
                        twilio_response = client.messages.create(body=message, to=number, from_=twilio_rule.from_number)
                except TwilioRestException as err:
                    LOG.error('TwilioRule: ERROR - %s', str(err))
                else:
                    LOG.info('TwilioRule: INFO - %s', twilio_response)

    def status_change(self, alert, status, text, **kwargs):
        return

    def take_action(self, alert, action, text, **kwargs):
        raise NotImplementedError

    def delete(self, alert, **kwargs) -> bool:
        raise NotImplementedError

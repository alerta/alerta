import abc

from flask import Blueprint, request, current_app
from six import add_metaclass

webhooks = Blueprint('webhooks', __name__)

from . import cloudwatch, grafana, graylog, newrelic, pagerduty, pingdom, prometheus, riemann
from . import serverdensity, slack, stackdriver, telegram, custom


@webhooks.before_request
def before_request():
    current_app.logger.info('Webhook Request:\n{} {}\n\n{}{}'.format(
        request.method,
        request.url,
        request.headers,
        request.get_data().decode('utf-8')
    ))


@add_metaclass(abc.ABCMeta)
class WebhookBase(object):

    def __init__(self, name=None):
        self.name = name or self.__module__

    @abc.abstractmethod
    def incoming(self, query_string, payload):
        """Parse webhook query string and/or payload in JSON or plain text and return an alert."""
        return

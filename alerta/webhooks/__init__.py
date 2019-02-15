import abc
import logging
from typing import Any, Union, Dict

from flask import Blueprint, request, current_app
from six import add_metaclass
from werkzeug.datastructures import ImmutableMultiDict

from alerta.models.alert import Alert

webhooks = Blueprint('webhooks', __name__)

from . import custom  # noqa

JSON = Dict[str, Any]


@webhooks.before_request
def before_request():
    current_app.logger.info('Webhook Request:\n{} {}\n\n{}{}'.format(
        request.method,
        request.url,
        request.headers,
        request.get_data().decode('utf-8')
    ))


LOG = logging.getLogger('alerta.webhooks')


@add_metaclass(abc.ABCMeta)
class WebhookBase:

    def __init__(self, name: str=None) -> None:
        self.name = name or self.__module__
        if self.__doc__:
            LOG.info('\n{}\n'.format(self.__doc__))

    @abc.abstractmethod
    def incoming(self, query_string: ImmutableMultiDict, payload: Any) -> Union[Alert, JSON]:
        """
        Parse webhook query string and/or payload in JSON or plain text and
        return an alert or a custom JSON response.
        """
        raise NotImplementedError

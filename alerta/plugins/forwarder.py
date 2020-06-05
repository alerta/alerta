import logging
from typing import TYPE_CHECKING, Any, Optional

from flask import request

from alerta.exceptions import ForwardingLoop
from alerta.plugins import PluginBase
from alerta.utils.client import Client
from alerta.utils.response import base_url

if TYPE_CHECKING:
    from alerta.models.alert import Alert  # noqa


LOG = logging.getLogger('alerta.plugins.forwarder')

X_LOOP_HEADER = 'X-Alerta-Loop'


def append_to_header(origin):
    x_loop = request.headers.get(X_LOOP_HEADER)
    return origin if not x_loop else '{},{}'.format(x_loop, origin)


def is_in_xloop(server):
    x_loop = request.headers.get(X_LOOP_HEADER)
    return server in x_loop if server and x_loop else False


class Forwarder(PluginBase):
    """
    Alert and action forwarder for federated Alerta deployments
    See https://docs.alerta.io/en/latest/federated.html
    """

    def pre_receive(self, alert: 'Alert', **kwargs) -> 'Alert':

        if is_in_xloop(base_url()):
            http_origin = request.origin or '(unknown)'  # type: ignore
            raise ForwardingLoop('Alert forwarded by {} already processed by {}'.format(http_origin, base_url()))
        return alert

    def post_receive(self, alert: 'Alert', **kwargs) -> Optional['Alert']:

        for remote, auth, actions in self.get_config('FWD_DESTINATIONS', default=[], type=list, **kwargs):
            if is_in_xloop(remote):
                LOG.debug('Forward [action=alerts]: {} ; Remote {} already processed alert. Skip.'.format(alert.id, remote))
                continue
            if not ('*' in actions or 'alerts' in actions):
                LOG.debug('Forward [action=alerts]: {} ; Remote {} not configured for alerts. Skip.'.format(alert.id, remote))
                continue

            headers = {X_LOOP_HEADER: append_to_header(base_url())}
            client = Client(endpoint=remote, headers=headers, **auth)

            LOG.info('Forward [action=alerts]: {} ; {} -> {}'.format(alert.id, base_url(), remote))
            try:
                r = client.send_alert(**alert.get_body())
            except Exception as e:
                LOG.warning('Forward [action=alerts]: {} ; Failed to forward alert to {} - {}'.format(alert.id, remote, str(e)))
                continue
            LOG.debug('Forward [action=alerts]: {} ; [{}] {}'.format(alert.id, r.status_code, r.text))

        return alert

    def status_change(self, alert: 'Alert', status: str, text: str, **kwargs) -> Any:
        return

    def take_action(self, alert: 'Alert', action: str, text: str, **kwargs) -> Any:

        if is_in_xloop(base_url()):
            http_origin = request.origin or '(unknown)'  # type: ignore
            raise ForwardingLoop('Action {} forwarded by {} already processed by {}'.format(
                action, http_origin, base_url())
            )

        for remote, auth, actions in self.get_config('FWD_DESTINATIONS', default=[], type=list, **kwargs):
            if is_in_xloop(remote):
                LOG.debug('Forward [action={}]: {} ; Remote {} already processed action. Skip.'.format(action, alert.id, remote))
                continue
            if not ('*' in actions or 'actions' in actions or action in actions):
                LOG.debug('Forward [action={}]: {} ; Remote {} not configured for action. Skip.'.format(action, alert.id, remote))
                continue

            headers = {X_LOOP_HEADER: append_to_header(base_url())}
            client = Client(endpoint=remote, headers=headers, **auth)

            LOG.info('Forward [action={}]: {} ; {} -> {}'.format(action, alert.id, base_url(), remote))
            try:
                r = client.action(alert.id, action, text)
            except Exception as e:
                LOG.warning('Forward [action={}]: {} ; Failed to action alert on {} - {}'.format(action, alert.id, remote, str(e)))
                continue
            LOG.debug('Forward [action={}]: {} ; [{}] {}'.format(action, alert.id, r.status_code, r.text))

        return alert

    def delete(self, alert: 'Alert', **kwargs) -> bool:

        if is_in_xloop(base_url()):
            http_origin = request.origin or '(unknown)'  # type: ignore
            raise ForwardingLoop('Delete forwarded by {} already processed by {}'.format(http_origin, base_url()))

        for remote, auth, actions in self.get_config('FWD_DESTINATIONS', default=[], type=list, **kwargs):
            if is_in_xloop(remote):
                LOG.debug('Forward [action=delete]: {} ; Remote {} already processed delete. Skip.'.format(alert.id, remote))
                continue
            if not ('*' in actions or 'delete' in actions):
                LOG.debug('Forward [action=delete]: {} ; Remote {} not configured for deletes. Skip.'.format(alert.id, remote))
                continue

            headers = {X_LOOP_HEADER: append_to_header(base_url())}
            client = Client(endpoint=remote, headers=headers, **auth)

            LOG.info('Forward [action=delete]: {} ; {} -> {}'.format(alert.id, base_url(), remote))
            try:
                r = client.delete_alert(alert.id)
            except Exception as e:
                LOG.warning('Forward [action=delete]: {} ; Failed to delete alert on {} - {}'.format(alert.id, remote, str(e)))
                continue
            LOG.debug('Forward [action=delete]: {} ; [{}] {}'.format(alert.id, r.status_code, r.text))

        return True  # always continue with local delete even if remote delete(s) fail

import logging

from flask import request

from alerta.plugins import PluginBase

LOG = logging.getLogger('alerta.plugins')


class RemoteIpAddr(PluginBase):
    """
    Add originating IP address of HTTP client as an alert attribute. This information
    can be used for debugging, access control, or generating geolocation data.
    """

    def pre_receive(self, alert, **kwargs):
        if request.headers.getlist('X-Forwarded-For'):
            alert.attributes.update(ip=request.headers.getlist('X-Forwarded-For')[0])
        else:
            alert.attributes.update(ip=request.remote_addr)
        return alert

    def post_receive(self, alert, **kwargs):
        return

    def status_change(self, alert, status, text, **kwargs):
        return

    def take_action(self, alert, action, text, **kwargs):
        raise NotImplementedError

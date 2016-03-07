
from alerta.plugins import PluginBase


class EnhanceAlert(PluginBase):

    def pre_receive(self, alert):
        if 'TPS reports' in alert.text:
            alert.attributes['customer'] = 'Initech'
        elif 'nexus' in alert.text:
            alert.attributes['customer'] = 'Tyrell Corp.'
        elif 'green wafer' in alert.text:
            alert.attributes['customer'] = 'Soylent Corp.'
        elif 'Skynet' in alert.text:
            alert.attributes['customer'] = 'Cyberdyne Systems'
        else:
            alert.attributes['customer'] = 'ACME Corp.'

        alert.attributes['runBookUrl'] = 'http://www.mywiki.org/RunBook/%s' % alert.event.replace(' ', '-')

        return alert

    def post_receive(self, alert):
        return

    def status_change(self, alert, status, text):
        return

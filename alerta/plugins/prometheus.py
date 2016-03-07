
import datetime
import requests

from alerta.app import app
from alerta.plugins import PluginBase

LOG = app.logger


ALERTMANAGER_API_URL = 'http://localhost:9093'
ALERTMANAGER_API_KEY = ''  # not used
ALERTMANAGER_SILENCE_DAYS = 1


class AlertmanagerSilence(PluginBase):

    def pre_receive(self, alert):
        return alert

    def post_receive(self, alert):
        return

    def status_change(self, alert, status, text):
        if alert.event_type != 'prometheusAlert':
            return

        if alert.status == status:
            return

        if status == 'ack':

            url = ALERTMANAGER_API_URL + '/api/v1/silences'

            data = {
                "matchers": [
                    {
                      "name": "alertname",
                      "value": alert.event
                    },
                    {
                      "name": "instance",
                      "value": alert.resource
                    }
                ],
                "startsAt": datetime.datetime.utcnow().replace(microsecond=0).isoformat() + ".000Z",
                "endsAt": (datetime.datetime.utcnow() + datetime.timedelta(days=ALERTMANAGER_SILENCE_DAYS))
                              .replace(microsecond=0).isoformat() + ".000Z",
                "createdBy": "alerta",
                "comment": text if text != '' else "silenced by alerta"
            }
            LOG.debug('Alertmanager payload: %s', data)

            LOG.debug('Alertmanager sending silence request to %s', url)
            try:
                r = requests.post(url, json=data, timeout=2)
            except Exception as e:
                raise RuntimeError("Alertmanager connection error: %s", e)

            LOG.debug('Alertmanager response: %s - %s', r.status_code, r.text)

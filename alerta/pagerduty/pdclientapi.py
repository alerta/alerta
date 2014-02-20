
import json
import requests

from alerta.common import config
from alerta.common import log as logging

LOG = logging.getLogger(__name__)
CONF = config.CONF


class PagerDutyClient(object):

    def __init__(self):

        self.REST_API = 'https://%s.pagerduty.com/api/v1' % CONF.pagerduty_subdomain
        self.INCIDENT_API = 'https://events.pagerduty.com/generic/2010-04-15/create_event.json'
        self.services = None

        self.get_services()

    def get_services(self):

        url = self.REST_API + '/services'
        headers = {'Authorization': 'Token token=%s' % CONF.pagerduty_api_key}
        response = requests.get(url, headers=headers).json()

        LOG.info('PagerDuty REST API response: %s', response)

        data = response['services']
        self.services = dict([(s['name'], s['service_key']) for s in data
                              if s['type'] == 'generic_events_api' and s['status'] == 'active'])

        for service, key in self.services.iteritems():
            LOG.info('Discovered active PagerDuty service %s with API key %s', service, key)

    def trigger_event(self, alert):

        service = alert.tags['pagerduty']
        incident_key = '-'.join(alert.service)

        if service not in self.services:
            LOG.error('Failed to send trigger event to PagerDuty - unknown service "%s"', service)
            return

        event = {
            "service_key": self.services[service],
            "event_type": "trigger",
            "description": alert.summary,
            "incident_key": incident_key,
            "client": "alerta",
            "client_url": "http://monitoring.guprod.gnm/alerta/widgets/v2/details?id=%s" % alert.get_id(),
            "details": {
                "severity": '%s -> %s' % (alert.previous_severity, alert.severity),
                "status": alert.status,
                "lastReceiveTime": alert.get_last_receive_time(),
                "environment": ",".join(alert.environment),
                "service": ",".join(alert.service),
                "resource": alert.resource,
                "event": alert.event,
                "value": alert.value,
                "text": alert.text,
                "id": alert.get_id(),
                "tags": ", ".join(k + '=' + v for k, v in alert.tags.items()),
                "moreInfo": alert.more_info
            }
        }
        LOG.info('PagerDuty TRIGGER event for %s => %s', service, event)

        self._submit_event(event)

    def acknowledge_event(self, alert):

        service = alert.tags['pagerduty']
        incident_key = '-'.join(alert.service)

        if service not in self.services:
            LOG.error('Failed to send acknowledge event to PagerDuty - unknown service "%s"', service)
            return

        event = {
            "service_key": self.services[service],
            "event_type": "acknowledge",
            "description": alert.summary,
            "incident_key": incident_key,
            "client": "alerta",
            "client_url": "http://monitoring.guprod.gnm/alerta/widgets/v2/details?id=%s" % alert.get_id(),
            "details": {
                "severity": '%s -> %s' % (alert.previous_severity, alert.severity),
                "status": alert.status,
                "lastReceiveTime": alert.get_last_receive_time(),
                "environment": ",".join(alert.environment),
                "service": ",".join(alert.service),
                "resource": alert.resource,
                "event": alert.event,
                "value": alert.value,
                "text": alert.text,
                "id": alert.get_id(),
                "tags": ", ".join(k + '=' + v for k, v in alert.tags.items()),
                "moreInfo": alert.more_info
            }
        }
        LOG.info('PagerDuty ACK event for %s => %s', service, event)

        self._submit_event(event)

    def resolve_event(self, alert):

        service = alert.tags['pagerduty']
        incident_key = '-'.join(alert.service)

        if service not in self.services:
            LOG.error('Failed to send resolve event to PagerDuty - unknown service "%s"', service)
            return

        event = {
            "service_key": self.services[service],
            "event_type": "resolve",
            "description": alert.summary,
            "incident_key": incident_key,
            "client": "alerta",
            "client_url": "http://monitoring.guprod.gnm/alerta/widgets/v2/details?id=%s" % alert.get_id(),
            "details": {
                "severity": '%s -> %s' % (alert.previous_severity, alert.severity),
                "status": alert.status,
                "lastReceiveTime": alert.get_last_receive_time(),
                "environment": ",".join(alert.environment),
                "service": ",".join(alert.service),
                "resource": alert.resource,
                "event": alert.event,
                "value": alert.value,
                "text": alert.text,
                "id": alert.get_id(),
                "tags": ", ".join(k + '=' + v for k, v in alert.tags.items()),
                "moreInfo": alert.more_info
            }
        }
        LOG.info('PagerDuty RESOLVE event for %s => %s', service, event)

        self._submit_event(event)

    def _submit_event(self, event):

        url = self.INCIDENT_API
        response = requests.post(url, data=json.dumps(event)).json()

        LOG.info('PagerDuty Integration API response: %s', response)

        if 'status' in response and response["status"] == "success":
            LOG.info('PagerDuty event for incident key %s triggered successfully by alert %s.',
                     event['incident_key'], event['details']['id'])
        else:
            LOG.error('PagerDuty server REJECTED alert %s: %s', event['details']['id'], response)






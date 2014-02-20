
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
        self.services = dict()

        self.get_services()

    def get_services(self):

        response = self._query('/services')
        services = response['services']
        self.services = dict([(s['name'], {'id': s['id'], 'key': s['service_key']}) for s in services
                              if s['type'] == 'generic_events_api'])

        for service, key in self.services.iteritems():
            LOG.info('Discovered PagerDuty service %s [id:%s] with API key %s',
                     service, self.services[service]['id'], self.services[service]['key'])

    def get_service_status(self, service):

        response = self._query('/services')
        services = response['services']
        for s in services:
            if s['name'] == service:
                return s['status']
        return None

    def _query(self, path):

        url = self.REST_API + path
        headers = {'Authorization': 'Token token=%s' % CONF.pagerduty_api_key}
        try:
            response = requests.get(url, headers=headers).json()
        except requests.ConnectionError, e:
            LOG.error('PagerDuty service request failed %s - %s', url, e)
            return None

        LOG.debug('PagerDuty %s query: %s', path, response)

        return response

    def trigger_event(self, alert):

        service = alert.tags['pagerduty']
        incident_key = '-'.join(alert.service)

        if service not in self.services:
            LOG.error('Failed to send trigger event to PagerDuty - unknown service "%s"', service)
            return

        current_status = self.get_service_status(service)
        if current_status != 'active':
            LOG.warn('Status for PagerDuty service %s is %s', service, current_status)

        event = {
            "service_key": self.services[service]['key'],
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

        current_status = self.get_service_status(service)
        if current_status != 'active':
            LOG.warn('Status for PagerDuty service %s is %s', service, current_status)

        event = {
            "service_key": self.services[service]['key'],
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

        current_status = self.get_service_status(service)
        if current_status != 'active':
            LOG.warn('Status for PagerDuty service %s is %s', service, current_status)

        event = {
            "service_key": self.services[service]['key'],
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
        data = json.dumps(event)
        try:
            response = requests.post(url, data=data).json()
        except requests.ConnectionError, e:
            LOG.error('PagerDuty incident request failed %s - %s', url, e)
            return

        LOG.debug('PagerDuty Integration API response: %s', response)

        if 'status' in response and response["status"] == "success":
            LOG.info('PagerDuty event for incident key %s triggered successfully by alert %s.',
                     event['incident_key'], event['details']['id'])
        else:
            LOG.error('PagerDuty server REJECTED alert %s: %s', event['details']['id'], response)






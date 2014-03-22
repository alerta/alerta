
import sys
import json
import requests
import requests.exceptions

from alerta.common import config
from alerta.common import log as logging

LOG = logging.getLogger(__name__)
CONF = config.CONF


class PagerDutyClient(object):

    def __init__(self):

        if not CONF.pagerduty_subdomain:
            LOG.error('Must specify PagerDuty subdomain')
            sys.exit(1)

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

    def get_incident_counts(self, service):

        response = self._query('/services')
        services = response['services']
        for s in services:
            if s['name'] == service:
                return s['incident_counts']
        return {}

    def _query(self, path):

        url = self.REST_API + path
        headers = {'Authorization': 'Token token=%s' % CONF.pagerduty_api_key}

        try:
            response = requests.get(url, headers=headers)
        except requests.ConnectionError, e:
            LOG.error('PagerDuty API request %s failed due to an ambiguous error - %s', url, e)
            sys.exit(1)

        try:
            response = response.json()
        except ValueError:
            LOG.error('PagerDuty API request %s failed - %s', url, response.text)
            sys.exit(1)

        if 'error' in response:
            LOG.error('PagerDuty API request %s failed - %s', url, response['error']['message'])
            sys.exit(1)

        LOG.debug('PagerDuty %s query: %s', path, response)

        return response

    def trigger_event(self, alert, service, incident_key):

        if service not in self.services:
            LOG.error('Failed to send trigger event to PagerDuty - unknown service "%s"', service)
            return

        current_status = self.get_service_status(service)
        if current_status != 'active':
            LOG.warn('Status for PagerDuty service %s is %s', service, current_status)

        event = {
            "service_key": self.services[service]['key'],
            "event_type": "trigger",
            "description": '%s: %s %s on %s %s' % (alert.environment, alert.severity, alert.event,
                                                   ','.join(alert.service), alert.resource),
            "incident_key": incident_key,
            "client": "alerta",
            "client_url": "http://monitoring.guprod.gnm/alerta/widgets/v2/details?id=%s" % alert.get_id(),
            "details": {
                "severity": '%s -> %s' % (alert.previous_severity, alert.severity),
                "status": alert.status,
                "lastReceiveTime": alert.get_date('last_receive_time', 'iso'),
                "environment": alert.environment,
                "service": ",".join(alert.service),
                "resource": alert.resource,
                "event": alert.event,
                "value": alert.value,
                "text": alert.text,
                "id": alert.get_id(),
                "tags": ", ".join(alert.tags)

            }
        }
        LOG.debug('PagerDuty TRIGGER event for %s => %s', service, event)

        self._submit_event(event)

        counts = self.get_incident_counts(service)
        LOG.info('PagerDuty %s incident counts: triggered=%s, acknowledged=%s, resolved=%s, total=%s',
                 service, counts['triggered'], counts['acknowledged'], counts['resolved'], counts['total'])

    def acknowledge_event(self, alert, service, incident_key):

        if service not in self.services:
            LOG.error('Failed to send acknowledge event to PagerDuty - unknown service "%s"', service)
            return

        current_status = self.get_service_status(service)
        if current_status != 'active':
            LOG.warn('Status for PagerDuty service %s is %s', service, current_status)

        event = {
            "service_key": self.services[service]['key'],
            "event_type": "acknowledge",
            "description": '%s: %s %s on %s %s' % (alert.environment, alert.severity, alert.event,
                                                   ','.join(alert.service), alert.resource),
            "incident_key": incident_key,
            "client": "alerta",
            "client_url": "http://monitoring.guprod.gnm/alerta/widgets/v2/details?id=%s" % alert.get_id(),
            "details": {
                "severity": '%s -> %s' % (alert.previous_severity, alert.severity),
                "status": alert.status,
                "lastReceiveTime": alert.get_date('last_receive_time', 'iso'),
                "environment": alert.environment,
                "service": ",".join(alert.service),
                "resource": alert.resource,
                "event": alert.event,
                "value": alert.value,
                "text": alert.text,
                "id": alert.get_id(),
                "tags": ", ".join(alert.tags)
            }
        }
        LOG.debug('PagerDuty ACK event for %s => %s', service, event)

        self._submit_event(event)

        counts = self.get_incident_counts(service)
        LOG.info('PagerDuty %s incident counts: triggered=%s, acknowledged=%s, resolved=%s, total=%s',
                 service, counts['triggered'], counts['acknowledged'], counts['resolved'], counts['total'])

    def resolve_event(self, alert, service, incident_key):

        if service not in self.services:
            LOG.error('Failed to send resolve event to PagerDuty - unknown service "%s"', service)
            return

        current_status = self.get_service_status(service)
        if current_status != 'active':
            LOG.warn('Status for PagerDuty service %s is %s', service, current_status)

        event = {
            "service_key": self.services[service]['key'],
            "event_type": "resolve",
            "description": '%s: %s %s on %s %s' % (alert.environment, alert.severity, alert.event,
                                                   ','.join(alert.service), alert.resource),
            "incident_key": incident_key,
            "client": "alerta",
            "client_url": "http://monitoring.guprod.gnm/alerta/widgets/v2/details?id=%s" % alert.get_id(),
            "details": {
                "severity": '%s -> %s' % (alert.previous_severity, alert.severity),
                "status": alert.status,
                "lastReceiveTime": alert.get_date('last_receive_time', 'iso'),
                "environment": alert.environment,
                "service": ",".join(alert.service),
                "resource": alert.resource,
                "event": alert.event,
                "value": alert.value,
                "text": alert.text,
                "id": alert.get_id(),
                "tags": ", ".join(alert.tags)
            }
        }
        LOG.debug('PagerDuty RESOLVE event for %s => %s', service, event)

        self._submit_event(event)

        counts = self.get_incident_counts(service)
        LOG.info('PagerDuty %s incident counts: triggered=%s, acknowledged=%s, resolved=%s, total=%s',
                 service, counts['triggered'], counts['acknowledged'], counts['resolved'], counts['total'])

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
            LOG.info('PagerDuty event triggered successfully by alert with incident_key=%s', event['incident_key'])
        else:
            LOG.error('PagerDuty server REJECTED alert %s: %s', event['details']['id'], response)


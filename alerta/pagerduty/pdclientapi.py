
import json
import datetime
import urllib2

from alerta.common import config
from alerta.common import log as logging

LOG = logging.getLogger(__name__)
CONF = config.CONF


class PagerDutyClient(object):

    def trigger_event(self, alert):

        incident_key = '-'.join(alert.service)

        pagerduty_event = {
            "service_key": CONF.pagerduty_api_key,
            "event_type": "trigger",
            "description": alert.summary,
            "incident_key": incident_key,
            "details": str(alert.get_body())
        }
        LOG.info('PagerDuty trigger event => %s', pagerduty_event)

        self._submit_event(alert.get_id(), pagerduty_event)

    def acknowledge_event(self, alert):

        incident_key = '-'.join(alert.service)

        pagerduty_event = {
            "service_key": CONF.pagerduty_api_key,
            "event_type": "acknowledge",
            "description": "someone is working on the problem",  # FIXME
            "incident_key": incident_key,
            "details": {"acked_at": str(datetime.datetime.utcnow())}  # FIXME
        }
        LOG.info('PagerDuty acknowledge event => %s', pagerduty_event)

        self._submit_event(alert.get_id(), pagerduty_event)

    def resolve_event(self, alert):

        incident_key = '-'.join(alert.service)

        pagerduty_event = {
            "service_key": CONF.pagerduty_api_key,
            "event_type": "resolve",
            "description": "someone fixed the problem",  # FIXME
            "incident_key": incident_key,
            "details": {"fixed_at": str(datetime.datetime.utcnow())}  # FIXME
        }
        LOG.info('PagerDuty resolve event => %s', pagerduty_event)

        self._submit_event(alert.get_id(), pagerduty_event)

    def _submit_event(self, alertid, event):

        incident_key = None
        retry = False

        try:
            request = urllib2.Request(CONF.pagerduty_endpoint)
            request.add_header("Content-type", "application/json")
            request.add_data(json.dumps(event))
            response = urllib2.urlopen(request)
            result = json.loads(response.read())

            if result["status"] == "success":
                incident_key = result["incident_key"]
                LOG.info('PagerDuty event triggered successfully by alert %s.', alertid)
            else:
                LOG.warn('PagerDuty server REJECTED alert %s: %s', alertid, result)

        except urllib2.URLError as e:
            # client error
            if e.code >= 400 and e.code < 500:
                LOG.warn('PagerDuty server REJECTED alert %s: %s', alertid, e.read())
            else:
                LOG.warn('PagerDuty server error for alert %s: %s', alertid, e.code, e.reason)
                retry = True  # We'll need to retry

        return retry, incident_key





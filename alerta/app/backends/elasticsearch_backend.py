
import datetime
import logging

from elasticsearch import Elasticsearch

from alerta.app import app, severity_code, status_code
from alerta.app.backends import Backend
from alerta.alert import AlertDocument
from alerta.heartbeat import HeartbeatDocument

logging.getLogger()
logging.basicConfig(level=logging.DEBUG)

# LOG = app.logger


class ElasticsearchBackend(Backend):

    def __init__(self):

        self.es = Elasticsearch()

    def get_count(self, query=None):
        """
        Return total number of alerts that meet the query filter.
        """
        query = {"query": {"match_all": {}}}

        return self.es.search(index="alerta", body=query)['hits']['total']

    def get_alerts(self, query=None, fields=None, sort=None, limit=0):

        query = {"query": {"match_all": {}}}

        responses = self.es.search(index="alerta", body=query)

        alerts = list()
        for hit in responses['hits']['hits']:
            response = hit['_source']
            print type(response['lastReceiveTime'])
            alerts.append(
                AlertDocument(
                    id=response.get('id', 'no-id'),
                    resource=response['resource'],
                    event=response['event'],
                    environment=response['environment'],
                    severity=response['severity'],
                    correlate=response['correlate'],
                    status=response['status'],
                    service=response['service'],
                    group=response['group'],
                    value=response['value'],
                    text=response['text'],
                    tags=response['tags'],
                    attributes=response['attributes'],
                    origin=response['origin'],
                    event_type=response['type'],
                    create_time=datetime.datetime.strptime(response['createTime'], "%Y-%m-%dT%H:%M:%S.%f"),
                    timeout=response['timeout'],
                    raw_data=response['rawData'],
                    duplicate_count=response['duplicateCount'],
                    repeat=response['repeat'],
                    previous_severity=response['previousSeverity'],
                    trend_indication=response['trendIndication'],
                    receive_time=datetime.datetime.strptime(response['receiveTime'], "%Y-%m-%dT%H:%M:%S.%f"),
                    last_receive_id=response['lastReceiveId'],
                    last_receive_time=datetime.datetime.strptime(response['lastReceiveTime'], "%Y-%m-%dT%H:%M:%S.%f"),
                    history=response['history']
                )
            )
        return alerts

    def create_alert(self, alert):

        trend_indication = severity_code.trend(severity_code.UNKNOWN, alert.severity)
        if alert.status == status_code.UNKNOWN:
                    status = severity_code.status_from_severity(severity_code.UNKNOWN, alert.severity)
        else:
            status = alert.status

        now = datetime.datetime.utcnow()
        history = [{
            "id": alert.id,
            "event": alert.event,
            "severity": alert.severity,
            "value": alert.value,
            "text": alert.text,
            "updateTime": alert.create_time
        }]
        if status != alert.status:
            history.append({
                "event": alert.event,
                "status": status,
                "text": "new alert status change",
                "id": alert.id,
                "updateTime": now
            })

        alert = {
            "foo": alert.id,
            "resource": alert.resource,
            "event": alert.event,
            "environment": alert.environment,
            "severity": alert.severity,
            "correlate": alert.correlate,
            "status": status,
            "service": alert.service,
            "group": alert.group,
            "value": alert.value,
            "text": alert.text,
            "tags": alert.tags,
            "attributes": alert.attributes,
            "origin": alert.origin,
            "type": alert.event_type,
            "createTime": alert.create_time,
            "timeout": alert.timeout,
            "rawData": alert.raw_data,
            "duplicateCount": 0,
            "repeat": False,
            "previousSeverity": severity_code.UNKNOWN,
            "trendIndication": trend_indication,
            "receiveTime": now,
            "lastReceiveId": alert.id,
            "lastReceiveTime": now,
            "history": history
        }

        # LOG.debug('Insert new alert in database: %s', alert)

        try:
            response = self.es.index(index="alerta", doc_type='alert', body=alert)
        except Exception as e:
            # LOG.error(e)
            return

        if not response:
            return

        return AlertDocument(
            id=alert['_id'],
            resource=alert['resource'],
            event=alert['event'],
            environment=alert['environment'],
            severity=alert['severity'],
            correlate=alert['correlate'],
            status=alert['status'],
            service=alert['service'],
            group=alert['group'],
            value=alert['value'],
            text=alert['text'],
            tags=alert['tags'],
            attributes=alert['attributes'],
            origin=alert['origin'],
            event_type=alert['type'],
            create_time=alert['createTime'],
            timeout=alert['timeout'],
            raw_data=alert['rawData'],
            duplicate_count=alert['duplicateCount'],
            repeat=alert['repeat'],
            previous_severity=alert['previousSeverity'],
            trend_indication=alert['trendIndication'],
            receive_time=alert['receiveTime'],
            last_receive_id=alert['lastReceiveId'],
            last_receive_time=alert['lastReceiveTime'],
            history=list()
        )

Elasticsearch
-------------

Query:

http://localhost:9200/alerta/alert/_search/

TODO
----

create
- new alert
- duplicate alert
- correlated alert

query
- get alert
- get alerts


update
- status


delete
- delete alert




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
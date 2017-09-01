from elasticsearch import Elasticsearch

from flask import current_app


class Backend:

    def connect(self, config):
        client = Elasticsearch([{'host': 'localhost', 'port': 9200}])
        self.create_indexes(client)
        return client

    @staticmethod
    def create_indexes(es):
        es.indices.create(index='alerts', ignore=400)

    def close(self):
        self.client.close()

    @property
    def client(self):
        return current_app.extensions['elasticsearch']

    ########################################

    def save_alert(self, alert):
        return self.client.index(index='alerts', doc_type='alert', id=alert.id, body=alert, refresh=True)

    def find_alert_by_id(self, id, customer=None):
        return self.client.get(index='alerts', doc_type='alert', id=id, refresh=True)

    def find_alerts_by_query(self, query=None, page=1, limit=0):
        # FIXME: build query, fields, sort from query and limit history
        return [a['_source'] for a in self.client.search('alerts', doc_type='alert', from_=(page-1)*limit, size=limit)['hits']['hits']]

    def get_counts_by_severity(self, query=None):
        raise NotImplementedError

    def get_counts_by_status(self, query=None):
        raise NotImplementedError

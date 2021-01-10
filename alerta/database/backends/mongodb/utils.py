import json
import re
from collections import namedtuple
from datetime import datetime

import pytz
from pyparsing import ParseException
from werkzeug.datastructures import ImmutableMultiDict, MultiDict

from alerta.exceptions import ApiError
from alerta.models.blackout import BlackoutStatus
from alerta.models.key import ApiKeyStatus
from alerta.utils.format import DateTime

from .queryparser import QueryParser

Query = namedtuple('Query', ['where', 'sort', 'group'])
Query.__new__.__defaults__ = ({}, {}, '_id', 'status')  # type: ignore


EXCLUDE_FROM_QUERY = [
    '_', 'callback', 'token', 'api-key', 'q', 'q.df', 'id', 'from-date', 'to-date',
    'sort-by', 'group-by', 'page', 'page-size', 'limit', 'show-raw-data', 'show-history'
]


class QueryBuilder:

    @staticmethod
    def sort_by_columns(params, valid_params):

        sort = list()
        direction = 1
        if params.get('sort-by', None):
            for sort_by in params.getlist('sort-by'):
                reverse = 1
                if sort_by.startswith('-'):
                    reverse = -1
                    sort_by = sort_by[1:]
                valid_sort_params = [k for k, v in valid_params.items() if v[1]]
                if sort_by not in valid_sort_params:
                    raise ApiError("Sorting by '{}' field not supported.".format(sort_by), 400)
                _, column, direction = valid_params[sort_by]
                sort.append((column, direction * reverse))
        else:
            sort.append(('_id', direction))
        return sort

    @staticmethod
    def filter_query(params, valid_params, query):

        for field in params.keys():
            if field.replace('!', '').split('.')[0] in EXCLUDE_FROM_QUERY:
                continue
            if field.replace('!', '').split('.')[0] not in valid_params:
                raise ApiError('Invalid filter parameter: {}'.format(field), 400)
            if field.startswith('attributes.'):
                column = field
            else:
                column, _, _ = valid_params[field.replace('!', '').split('.')[0]]
            value = params.getlist(field)
            if len(value) == 1:
                value = value[0]
                if field.endswith('!'):
                    if value.startswith('~'):
                        query[column] = dict()
                        query[column]['$not'] = re.compile(value[1:], re.IGNORECASE)
                    else:
                        query[column] = dict()
                        query[column]['$ne'] = value
                else:
                    if value.startswith('~'):
                        query[column] = dict()
                        query[column]['$regex'] = re.compile(value[1:], re.IGNORECASE)
                    else:
                        query[column] = value
            else:
                if field.endswith('!'):
                    if '~' in [v[0] for v in value]:
                        value = '|'.join([v.lstrip('~') for v in value])
                        query[column] = dict()
                        query[column]['$not'] = re.compile(value, re.IGNORECASE)
                    else:
                        query[column] = dict()
                        query[column]['$nin'] = value
                else:
                    if '~' in [v[0] for v in value]:
                        value = '|'.join([v.lstrip('~') for v in value])
                        query[column] = dict()
                        query[column]['$regex'] = re.compile(value, re.IGNORECASE)
                    else:
                        query[column] = dict()
                        query[column]['$in'] = value
        return query


class Alerts(QueryBuilder):

    VALID_PARAMS = {
        # field (column, sort-by, direction)
        'id': ('_id', None, 0),
        'resource': ('resource', 'resource', 1),
        'event': ('event', 'event', 1),
        'environment': ('environment', 'environment', 1),
        'severity': ('severity', 'code', 1),
        'correlate': ('correlate', 'correlate', 1),
        'status': ('status', 'state', 1),
        'service': ('service', 'service', 1),
        'group': ('group', 'group', 1),
        'value': ('value', 'value', 1),
        'text': ('text', 'text', 1),
        'tag': ('tags', None, 0),  # filter
        'tags': (None, 'tags', 1),  # sort-by
        'attributes': ('', '', 1),
        'origin': ('origin', 'origin', 1),
        'type': ('type', 'type', 1),
        'createTime': ('createTime', 'createTime', -1),
        'timeout': ('timeout', 'timeout', 1),
        'rawData': ('rawData', 'rawData', 1),
        'customer': ('customer', 'customer', 1),
        'duplicateCount': ('duplicateCount', 'duplicateCount', 1),
        'repeat': ('repeat', 'repeat', 1),
        'previousSeverity': ('previousSeverity', 'previousSeverity', 1),
        'trendIndication': ('trendIndication', 'trendIndication', 1),
        'receiveTime': ('receiveTime', 'receiveTime', -1),
        'lastReceiveId': ('lastReceiveId', 'lastReceiveId', 1),
        'lastReceiveTime': ('lastReceiveTime', 'lastReceiveTime', -1),
        'updateTime': ('updateTime', 'updateTime', -1),
    }

    @staticmethod
    def from_params(params: ImmutableMultiDict, customers=None, query_time=None):

        # ?q=
        if params.get('q', None):
            try:
                parser = QueryParser()
                query = json.loads(parser.parse(
                    query=params['q'],
                    default_field=params.get('q.df'),
                    default_operator=params.get('q.op')
                ))
            except ParseException as e:
                raise ApiError('Failed to parse query string.', 400, [e])
        else:
            query = dict()

        # customer
        if customers:
            customer_query = {'customer': {'$in': customers}}
        else:
            customer_query = None  # type: ignore

        # from-date, to-date
        from_date = params.get('from-date', default=None, type=DateTime.parse)
        to_date = params.get('to-date', default=query_time, type=DateTime.parse)

        if from_date and to_date:
            query['lastReceiveTime'] = {'$gt': from_date.replace(
                tzinfo=pytz.utc), '$lte': to_date.replace(tzinfo=pytz.utc)}
        elif to_date:
            query['lastReceiveTime'] = {'$lte': to_date.replace(tzinfo=pytz.utc)}

        # duplicateCount, repeat
        if params.get('duplicateCount', None):
            query['duplicateCount'] = params.get('duplicateCount', int)
        if params.get('repeat', None):
            query['repeat'] = params.get('repeat', default=True, type=lambda x: x == 'true')

        # id
        ids = params.getlist('id')
        if len(ids) == 1:
            query['$or'] = [{'_id': {'$regex': '^' + ids[0]}}, {'lastReceiveId': {'$regex': '^' + ids[0]}}]
        elif ids:
            query['$or'] = [{'_id': {'$regex': re.compile('|'.join(['^' + i for i in ids]))}},
                            {'lastReceiveId': {'$regex': re.compile('|'.join(['^' + i for i in ids]))}}]

        # filter, sort-by, group-by
        query = QueryBuilder.filter_query(params, Alerts.VALID_PARAMS, query)
        sort = QueryBuilder.sort_by_columns(params, Alerts.VALID_PARAMS)
        group = params.getlist('group-by')

        if customer_query:
            query = {'$and': [customer_query, query]}

        return Query(where=query, sort=sort, group=group)


class Blackouts(QueryBuilder):

    VALID_PARAMS = {
        # field (column, sort-by, direction)
        'id': ('_id', None, 0),
        'priority': ('priority', 'priority', 1),
        'environment': ('environment', 'environment', 1),
        'service': ('service', 'service', 1),
        'resource': ('resource', 'resource', 1),
        'event': ('event', 'event', 1),
        'group': ('"group"', '"group"', 1),
        'tag': ('tags', None, 0),  # filter
        'tags': (None, 'tags', 1),  # sort-by
        'customer': ('customer', 'customer', 1),
        'startTime': ('startTime', 'startTime', -1),
        'endTime': ('endTime', 'endTime', -1),
        'duration': ('duration', 'duration', 1),
        'status': ('status', 'status', 1),
        'remaining': ('remaining', 'remaining', -1),
        'user': ('user', 'user', 1),
        'createTime': ('createTime', 'createTime', -1),
        'text': ('text', 'text', 1),
    }

    @staticmethod
    def from_params(params: ImmutableMultiDict, customers=None, query_time=None):

        query = dict()
        params = MultiDict(params)

        # customer
        if customers:
            customer_query = {'customer': {'$in': customers}}
        else:
            customer_query = None  # type: ignore

        # status
        status = params.poplist('status')
        if status:
            query['$or'] = list()
            if BlackoutStatus.Active in status:
                query['$or'].append({'$and': [{'startTime': {'$lte': datetime.utcnow()}}, {'endTime': {'$gt': datetime.utcnow()}}]})
            if BlackoutStatus.Pending in status:
                query['$or'].append({'startTime': {'$gt': datetime.utcnow()}})
            if BlackoutStatus.Expired in status:
                query['$or'].append({'endTime': {'$lte': datetime.utcnow()}})

        # filter, sort-by, group-by
        query = QueryBuilder.filter_query(params, Blackouts.VALID_PARAMS, query)
        sort = QueryBuilder.sort_by_columns(params, Blackouts.VALID_PARAMS)

        if customer_query:
            query = {'$and': [customer_query, query]}

        return Query(where=query, sort=sort, group=None)


class Heartbeats(QueryBuilder):

    VALID_PARAMS = {
        # field (column, sort-by, direction)
        'id': ('_id', None, 0),
        'origin': ('origin', 'origin', 1),
        'tag': ('tags', None, 0),  # filter
        'tags': (None, 'tags', 1),  # sort-by
        'attributes': ('attributes', 'attributes', 1),
        'type': ('type', 'type', 1),
        'createTime': ('createTime', 'createTime', -1),
        'timeout': ('timeout', 'timeout', 1),
        'receiveTime': ('receiveTime', 'receiveTime', -1),
        'customer': ('customer', 'customer', 1),
        'latency': ('latency', 'latency', 1),
        'since': ('since', 'since', -1),
        'status': ('status', None, 0),
    }

    @staticmethod
    def from_params(params: ImmutableMultiDict, customers=None, query_time=None):

        query = dict()
        params = MultiDict(params)

        # customer
        if customers:
            customer_query = {'customer': {'$in': customers}}
        else:
            customer_query = None  # type: ignore

        # status filter implemented in database
        params.poplist('status')

        # filter, sort-by
        query = QueryBuilder.filter_query(params, Heartbeats.VALID_PARAMS, query)
        sort = QueryBuilder.sort_by_columns(params, Heartbeats.VALID_PARAMS)

        if customer_query:
            query = {'$and': [customer_query, query]}

        return Query(where=query, sort=sort, group=None)


class ApiKeys(QueryBuilder):

    VALID_PARAMS = {
        # field (column, sort-by, direction)
        'id': ('_id', None, 0),
        'key': ('key', 'key', 1),
        'status': ('status', 'status', 1),
        'user': ('user', 'user', 1),
        'scope': ('scopes', None, 0),  # filter
        'scopes': (None, 'scopes', 1),  # sort-by
        'type': ('type', 'type', 1),
        'text': ('text', 'text', 1),
        'expireTime': ('expireTime', 'expireTime', -1),
        'count': ('count', 'count', 1),
        'lastUsedTime': ('lastUsedTime', 'lastUsedTime', -1),
        'customer': ('customer', 'customer', 1),
    }

    @staticmethod
    def from_params(params: MultiDict, customers=None, query_time=None):

        query = dict()
        params = MultiDict(params)

        # customer
        if customers:
            customer_query = {'customer': {'$in': customers}}
        else:
            customer_query = None  # type: ignore

        # status
        status = params.poplist('status')
        if status:
            query['$or'] = list()
            if ApiKeyStatus.Active in status:
                query['$or'].append({'expireTime': {'$gte': datetime.utcnow()}})
            if ApiKeyStatus.Expired in status:
                query['$or'].append({'expireTime': {'$lt': datetime.utcnow()}})

        # filter, sort-by, group-by
        query = QueryBuilder.filter_query(params, ApiKeys.VALID_PARAMS, query)
        sort = QueryBuilder.sort_by_columns(params, ApiKeys.VALID_PARAMS)

        if customer_query:
            query = {'$and': [customer_query, query]}

        return Query(where=query, sort=sort, group=None)


class Users(QueryBuilder):

    VALID_PARAMS = {
        # field (column, sort-by, direction)
        'id': ('_id', None, 0),
        'name': ('name', 'name', 1),
        'login': ('login', 'login', 1),
        'email': ('email', 'email', 1),
        'domain': ('domain', 'domain', 1),
        'status': ('status', 'status', 1),
        'role': ('roles', None, 0),  # filter
        'roles': (None, 'roles', 1),  # sort-by
        'attributes': ('attributes', 'attributes', 1),
        'createTime': ('createTime', 'createTime', -1),
        'lastLogin': ('lastLogin', 'lastLogin', -1),
        'text': ('text', 'text', 1),
        'updateTime': ('updateTime', 'updateTime', -1),
        'email_verified': ('email_verified', 'email_verified', 1),
    }

    @staticmethod
    def from_params(params: MultiDict, customers=None, query_time=None):

        query = dict()
        params = MultiDict(params)

        # filter, sort-by, group-by
        query = QueryBuilder.filter_query(params, Users.VALID_PARAMS, query)
        sort = QueryBuilder.sort_by_columns(params, Users.VALID_PARAMS)

        return Query(where=query, sort=sort, group=None)


class Groups(QueryBuilder):

    VALID_PARAMS = {
        # field (column, sort-by, direction)
        'id': ('_id', None, 0),
        'name': ('name', 'name', 1),
        'text': ('text', 'text', 1),
        'count': ('count', 'count', 1),
    }

    @staticmethod
    def from_params(params: MultiDict, customers=None, query_time=None):

        query = dict()
        params = MultiDict(params)

        # filter, sort-by, group-by
        query = QueryBuilder.filter_query(params, Groups.VALID_PARAMS, query)
        sort = QueryBuilder.sort_by_columns(params, Groups.VALID_PARAMS)

        return Query(where=query, sort=sort, group=None)


class Permissions(QueryBuilder):

    VALID_PARAMS = {
        # field (column, sort-by, direction)
        'id': ('_id', None, 0),
        'match': ('match', 'match', 1),  # role
        'scope': ('scopes', None, 0),  # filter
        'scopes': (None, 'scopes', 1),  # sort-by
    }

    @staticmethod
    def from_params(params: MultiDict, customers=None, query_time=None):

        query = dict()
        params = MultiDict(params)

        # filter, sort-by, group-by
        query = QueryBuilder.filter_query(params, Permissions.VALID_PARAMS, query)
        sort = QueryBuilder.sort_by_columns(params, Permissions.VALID_PARAMS)

        return Query(where=query, sort=sort, group=None)


class Customers(QueryBuilder):

    VALID_PARAMS = {
        # field (column, sort-by, direction)
        'id': ('_id', None, 0),
        'match': ('match', 'match', 1),
        'customer': ('customer', 'customer', 1),
    }

    @staticmethod
    def from_params(params: MultiDict, customers=None, query_time=None):

        query = dict()
        params = MultiDict(params)

        # filter, sort-by, group-by
        query = QueryBuilder.filter_query(params, Customers.VALID_PARAMS, query)
        sort = QueryBuilder.sort_by_columns(params, Customers.VALID_PARAMS)

        return Query(where=query, sort=sort, group=None)

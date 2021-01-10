from collections import namedtuple
from typing import Any, Dict  # noqa

import pytz
from pyparsing import ParseException
from werkzeug.datastructures import MultiDict

from alerta.exceptions import ApiError
from alerta.models.blackout import BlackoutStatus
from alerta.models.key import ApiKeyStatus
from alerta.utils.format import DateTime

from .queryparser import QueryParser

Query = namedtuple('Query', ['where', 'vars', 'sort', 'group'])
Query.__new__.__defaults__ = ('1=1', {}, '(false)', 'status')  # type: ignore


EXCLUDE_FROM_QUERY = [
    '_', 'callback', 'token', 'api-key', 'q', 'q.df', 'id', 'from-date', 'to-date',
    'sort-by', 'group-by', 'page', 'page-size', 'limit', 'show-raw-data', 'show-history'
]


class QueryBuilder:

    @staticmethod
    def sort_by_columns(params, valid_params):

        sort = list()
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
                direction = 'ASC' if direction * reverse == 1 else 'DESC'
                sort.append('{} {}'.format(column, direction))
        else:
            sort.append('(false)')
        return sort

    @staticmethod
    def filter_query(params, valid_params, query, qvars):

        for field in params.keys():
            if field.replace('!', '').split('.')[0] in EXCLUDE_FROM_QUERY:  # eg. "attributes.foo!=bar" => 'attributes'
                continue
            valid_filter_params = [k for k, v in valid_params.items() if v[0]]
            if field.replace('!', '').split('.')[0] not in valid_filter_params:
                raise ApiError('Invalid filter parameter: {}'.format(field), 400)
            column, _, _ = valid_params[field.replace('!', '').split('.')[0]]
            value = params.getlist(field)

            if field in ['service', 'tags', 'roles', 'scopes']:
                query.append('AND {0} && %({0})s'.format(column))
                qvars[column] = value
            elif field.startswith('attributes.'):
                column = field.replace('attributes.', '')
                query.append('AND attributes @> %(attr_{})s'.format(column))
                qvars['attr_' + column] = {column: value[0]}
            elif len(value) == 1:
                value = value[0]
                if field.endswith('!'):
                    if value.startswith('~'):
                        query.append('AND NOT "{0}" ILIKE %(not_{0})s'.format(column))
                        qvars['not_' + column] = '%' + value[1:] + '%'
                    else:
                        query.append('AND "{0}"!=%(not_{0})s'.format(column))
                        qvars['not_' + column] = value
                else:
                    if value.startswith('~'):
                        query.append('AND "{0}" ILIKE %({0})s'.format(column))
                        qvars[column] = '%' + value[1:] + '%'
                    else:
                        query.append('AND "{0}"=%({0})s'.format(column))
                        qvars[column] = value
            else:
                if field.endswith('!'):
                    if '~' in [v[0] for v in value]:
                        query.append('AND "{0}" !~* (%(not_regex_{0})s)'.format(column))
                        qvars['not_regex_' + column] = '|'.join([v.lstrip('~') for v in value])
                    else:
                        query.append('AND NOT "{0}"=ANY(%(not_{0})s)'.format(column))
                        qvars['not_' + column] = value
                else:
                    if '~' in [v[0] for v in value]:
                        query.append('AND "{0}" ~* (%(regex_{0})s)'.format(column))
                        qvars['regex_' + column] = '|'.join([v.lstrip('~') for v in value])
                    else:
                        query.append('AND "{0}"=ANY(%({0})s)'.format(column))
                        qvars[column] = value
        return query, qvars


class Alerts(QueryBuilder):

    VALID_PARAMS = {
        # field (column, sort-by, direction)
        'id': ('id', None, 0),
        'resource': ('resource', 'resource', 1),
        'event': ('event', 'event', 1),
        'environment': ('environment', 'environment', 1),
        'severity': ('severity', 's.code', 1),
        'correlate': ('correlate', 'correlate', 1),
        'status': ('status', 'st.state', 1),
        'service': ('service', 'service', 1),
        'group': ('group', '"group"', 1),
        'value': ('value', 'value', 1),
        'text': ('text', 'text', 1),
        'tag': ('tags', None, 0),  # filter
        'tags': (None, 'tags', 1),  # sort-by
        'attributes': ('attributes', 'attributes', 1),
        'origin': ('origin', 'origin', 1),
        'type': ('event_type', 'event_type', 1),
        'createTime': ('create_time', 'create_time', -1),
        'timeout': ('timeout', 'timeout', 1),
        'rawData': ('raw_data', 'raw_data', 1),
        'customer': ('customer', 'customer', 1),
        'duplicateCount': ('duplicate_count', 'duplicate_count', 1),
        'repeat': ('repeat', 'repeat', 1),
        'previousSeverity': ('previous_severity', 'previous_severity', 1),
        'trendIndication': ('trend_indication', 'trend_indication', 1),
        'receiveTime': ('receive_time', 'receive_time', -1),
        'lastReceiveId': ('last_receive_id', 'last_receive_id', 1),
        'lastReceiveTime': ('last_receive_time', 'last_receive_time', -1),
        'updateTime': ('update_time', 'update_time', -1),
    }

    @staticmethod
    def from_params(params: MultiDict, customers=None, query_time=None):

        # ?q=
        if params.get('q', None):
            try:
                parser = QueryParser()
                query = [parser.parse(
                    query=params['q'],
                    default_field=params.get('q.df')
                )]
                qvars = dict()  # type: Dict[str, Any]
            except ParseException as e:
                raise ApiError('Failed to parse query string.', 400, [e])
        else:
            query = ['1=1']
            qvars = dict()

        # customer
        if customers:
            query.append('AND customer=ANY(%(customers)s)')
            qvars['customers'] = customers

        # from-date, to-date
        from_date = params.get('from-date', default=None, type=DateTime.parse)
        to_date = params.get('to-date', default=query_time, type=DateTime.parse)

        if from_date:
            query.append('AND last_receive_time > %(from_date)s')
            qvars['from_date'] = from_date.replace(tzinfo=pytz.utc)
        if to_date:
            query.append('AND last_receive_time <= %(to_date)s')
            qvars['to_date'] = to_date.replace(tzinfo=pytz.utc)

        # duplicateCount, repeat
        if params.get('duplicateCount', None):
            query.append('AND duplicate_count=%(duplicate_count)s')
            qvars['duplicate_count'] = params.get('duplicateCount', int)
        if params.get('repeat', None):
            query.append('AND repeat=%(repeat)s')
            qvars['repeat'] = params.get('repeat', default=True, type=lambda x: x.lower()
                                         in ['true', 't', '1', 'yes', 'y', 'on'])
        # id
        ids = params.getlist('id')
        if len(ids) == 1:
            query.append('AND (alerts.id LIKE %(id)s OR last_receive_id LIKE %(id)s)')
            qvars['id'] = ids[0] + '%'
        elif ids:
            query.append('AND (id ~* (%(regex_id)s) OR last_receive_id ~* (%(regex_id)s))')
            qvars['regex_id'] = '|'.join(['^' + i for i in ids])

        # filter, sort-by, group-by
        query, qvars = QueryBuilder.filter_query(params, Alerts.VALID_PARAMS, query, qvars)
        sort = QueryBuilder.sort_by_columns(params, Alerts.VALID_PARAMS)
        group = params.getlist('group-by')

        return Query(where='\n'.join(query), vars=qvars, sort=','.join(sort), group=group)


class Blackouts(QueryBuilder):

    VALID_PARAMS = {
        # field (column, sort-by, direction)
        'id': ('id', None, 0),
        'priority': ('priority', 'priority', 1),
        'environment': ('environment', 'environment', 1),
        'service': ('service', 'service', 1),
        'resource': ('resource', 'resource', 1),
        'event': ('event', 'event', 1),
        'group': ('group', '"group"', 1),
        'tag': ('tags', None, 0),  # filter
        'tags': (None, 'tags', 1),  # sort-by
        'customer': ('customer', 'customer', 1),
        'startTime': ('start_time', 'start_time', -1),
        'endTime': ('end_time', 'end_time', -1),
        'duration': ('duration', 'duration', 1),
        'status': ('status', 'status', 1),
        'remaining': ('remaining', 'remaining', -1),
        'user': ('user', 'user', 1),
        'createTime': ('create_time', 'create_time', -1),
        'text': ('text', 'text', 1),
    }

    @staticmethod
    def from_params(params: MultiDict, customers=None, query_time=None):

        query = ['1=1']
        qvars = dict()
        params = MultiDict(params)

        # customer
        if customers:
            query.append('AND customer=ANY(%(customers)s)')
            qvars['customers'] = customers

        # status
        status = params.poplist('status')
        if status:
            squery = list()
            if BlackoutStatus.Active in status:
                squery.append("(start_time <= NOW() at time zone 'utc' AND end_time > NOW())")
            if BlackoutStatus.Pending in status:
                squery.append("start_time > NOW() at time zone 'utc'")
            if BlackoutStatus.Expired in status:
                squery.append("end_time <= NOW() at time zone 'utc'")
            if squery:
                query.append('AND (' + ' OR '.join(squery) + ')')

        # filter, sort-by
        query, qvars = QueryBuilder.filter_query(params, Blackouts.VALID_PARAMS, query, qvars)
        sort = QueryBuilder.sort_by_columns(params, Blackouts.VALID_PARAMS)

        return Query(where='\n'.join(query), vars=qvars, sort=','.join(sort), group='')


class Heartbeats(QueryBuilder):

    VALID_PARAMS = {
        # field (column, sort-by, direction)
        'id': ('id', None, 0),
        'origin': ('origin', 'origin', 1),
        'tag': ('tags', None, 0),  # filter
        'tags': (None, 'tags', 1),  # sort-by
        'attributes': ('attributes', 'attributes', 1),
        'type': ('event_type', 'event_type', 1),
        'createTime': ('create_time', 'create_time', -1),
        'timeout': ('timeout', 'timeout', 1),
        'receiveTime': ('receive_time', 'receive_time', -1),
        'customer': ('customer', 'customer', 1),
        'latency': ('latency', 'latency', 1),
        'since': ('since', 'since', -1),
        'status': ('status', None, 0),
    }

    @staticmethod
    def from_params(params: MultiDict, customers=None, query_time=None):

        query = ['1=1']
        qvars = dict()
        params = MultiDict(params)

        # customer
        if customers:
            query.append('AND customer=ANY(%(customers)s)')
            qvars['customers'] = customers

        # status filter implemented in database
        params.poplist('status')

        # filter, sort-by
        query, qvars = QueryBuilder.filter_query(params, Heartbeats.VALID_PARAMS, query, qvars)
        sort = QueryBuilder.sort_by_columns(params, Heartbeats.VALID_PARAMS)

        return Query(where='\n'.join(query), vars=qvars, sort=','.join(sort), group='')


class ApiKeys(QueryBuilder):

    VALID_PARAMS = {
        # field (column, sort-by, direction)
        'id': ('id', None, 0),
        'key': ('key', 'key', 1),
        'status': ('status', 'status', 1),
        'user': ('user', 'user', 1),
        'scope': ('scopes', None, 0),  # filter
        'scopes': (None, 'scopes', 1),  # sort-by
        'type': ('type', 'type', 1),
        'text': ('text', 'text', 1),
        'expireTime': ('expire_time', 'expire_time', -1),
        'count': ('count', 'count', 1),
        'lastUsedTime': ('last_used_time', 'last_used_time', -1),
        'customer': ('customer', 'customer', 1),
    }

    @staticmethod
    def from_params(params: MultiDict, customers=None, query_time=None):

        query = ['1=1']
        qvars = dict()
        params = MultiDict(params)

        # customer
        if customers:
            query.append('AND customer=ANY(%(customers)s)')
            qvars['customers'] = customers

        # status
        status = params.poplist('status')
        if status:
            squery = list()
            if ApiKeyStatus.Active in status:
                squery.append("expire_time >= NOW() at time zone 'utc'")
            if ApiKeyStatus.Expired in status:
                squery.append("expire_time < NOW() at time zone 'utc'")
            if squery:
                query.append('AND (' + ' OR '.join(squery) + ')')

        # filter, sort-by
        query, qvars = QueryBuilder.filter_query(params, ApiKeys.VALID_PARAMS, query, qvars)
        sort = QueryBuilder.sort_by_columns(params, ApiKeys.VALID_PARAMS)

        return Query(where='\n'.join(query), vars=qvars, sort=','.join(sort), group='')


class Users(QueryBuilder):

    VALID_PARAMS = {
        # field (column, sort-by, direction)
        'id': ('id', None, 0),
        'name': ('name', 'name', 1),
        'login': ('login', 'login', 1),
        'email': ('email', 'email', 1),
        'domain': ('domain', 'domain', 1),
        'status': ('status', 'status', 1),
        'role': ('roles', None, 0),  # filter
        'roles': (None, 'roles', 1),  # sort-by
        'attributes': ('attributes', 'attributes', 1),
        'createTime': ('create_time', 'create_time', -1),
        'lastLogin': ('last_login', 'last_login', -1),
        'text': ('text', 'text', 1),
        'updateTime': ('update_time', 'update_time', -1),
        'email_verified': ('email_verified', 'email_verified', 1),
    }

    @staticmethod
    def from_params(params: MultiDict, customers=None, query_time=None):

        query = ['1=1']
        qvars = dict()
        params = MultiDict(params)

        # filter, sort-by
        query, qvars = QueryBuilder.filter_query(params, Users.VALID_PARAMS, query, qvars)
        sort = QueryBuilder.sort_by_columns(params, Users.VALID_PARAMS)

        return Query(where='\n'.join(query), vars=qvars, sort=','.join(sort), group='')


class Groups(QueryBuilder):

    VALID_PARAMS = {
        # field (column, sort-by, direction)
        'id': ('id', None, 0),
        'name': ('name', 'name', 1),
        'text': ('text', 'text', 1),
        'count': ('count', 'count', 1),
    }

    @staticmethod
    def from_params(params: MultiDict, customers=None, query_time=None):

        query = ['1=1']
        qvars = dict()
        params = MultiDict(params)

        # filter, sort-by
        query, qvars = QueryBuilder.filter_query(params, Groups.VALID_PARAMS, query, qvars)
        sort = QueryBuilder.sort_by_columns(params, Groups.VALID_PARAMS)

        return Query(where='\n'.join(query), vars=qvars, sort=','.join(sort), group='')


class Permissions(QueryBuilder):

    VALID_PARAMS = {
        # field (column, sort-by, direction)
        'id': ('id', None, 0),
        'match': ('match', 'match', 1),  # role
        'scope': ('scopes', None, 0),  # filter
        'scopes': (None, 'scopes', 1),  # sort-by
    }

    @staticmethod
    def from_params(params: MultiDict, customers=None, query_time=None):

        query = ['1=1']
        qvars = dict()
        params = MultiDict(params)

        # filter, sort-by
        query, qvars = QueryBuilder.filter_query(params, Permissions.VALID_PARAMS, query, qvars)
        sort = QueryBuilder.sort_by_columns(params, Permissions.VALID_PARAMS)

        return Query(where='\n'.join(query), vars=qvars, sort=','.join(sort), group='')


class Customers(QueryBuilder):

    VALID_PARAMS = {
        # field (column, sort-by, direction)
        'id': ('id', None, 0),
        'match': ('match', 'match', 1),
        'customer': ('customer', 'customer', 1),
    }

    @staticmethod
    def from_params(params: MultiDict, customers=None, query_time=None):

        query = ['1=1']
        qvars = dict()
        params = MultiDict(params)

        # filter, sort-by
        query, qvars = QueryBuilder.filter_query(params, Customers.VALID_PARAMS, query, qvars)
        sort = QueryBuilder.sort_by_columns(params, Customers.VALID_PARAMS)

        return Query(where='\n'.join(query), vars=qvars, sort=','.join(sort), group='')

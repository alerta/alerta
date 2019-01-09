from collections import namedtuple
from typing import Any, Dict  # noqa

import pytz
from pyparsing import ParseException
from werkzeug.datastructures import MultiDict

from alerta.database.base import QueryBuilder
from alerta.exceptions import ApiError
from alerta.utils.format import DateTime

from .queryparser import QueryParser

Query = namedtuple('Query', ['where', 'vars', 'sort', 'group'])
Query.__new__.__defaults__ = ('1=1', {}, 'last_receive_time', 'status')  # type: ignore


class QueryBuilderImpl(QueryBuilder):

    @staticmethod
    def from_params(params: MultiDict, customers=None, query_time=None):

        # q
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

        def reverse_sort(direction):
            return 'ASC' if direction == 'DESC' else 'DESC'

        # sort-by
        sort = list()
        direction = 'ASC'
        if params.get('reverse', None):
            direction = 'DESC'
        if params.get('sort-by', None):
            for sort_by in params.getlist('sort-by'):
                if sort_by == 'createTime':
                    sort.append('create_time ' + reverse_sort(direction))
                elif sort_by == 'receiveTime':
                    sort.append('receive_time ' + reverse_sort(direction))
                elif sort_by == 'lastReceiveTime':
                    sort.append('last_receive_time ' + reverse_sort(direction))
                elif sort_by == 'duplicateCount':
                    sort.append('duplicate_count ' + direction)
                else:
                    sort.append(sort_by + ' ' + direction)
        else:
            sort.append('last_receive_time ' + reverse_sort(direction))

        # group-by
        group = params.getlist('group-by')

        # id
        ids = params.getlist('id')
        if len(ids) == 1:
            query.append('AND (id LIKE %(id)s OR last_receive_id LIKE %(id)s)')
            qvars['id'] = ids[0] + '%'
        elif ids:
            query.append('AND (id ~* (%(regex_id)s) OR last_receive_id ~* (%(regex_id)s))')
            qvars['regex_id'] = '|'.join(['^' + i for i in ids])

        EXCLUDE_QUERY = ['_', 'callback', 'token', 'api-key', 'q', 'q.df', 'id',
                         'from-date', 'to-date', 'duplicateCount', 'repeat', 'sort-by',
                         'reverse', 'group-by', 'page', 'page-size', 'limit']

        # fields
        for field in params:
            if field in EXCLUDE_QUERY:
                continue
            value = params.getlist(field)
            if field in ['service', 'tags', 'roles', 'scopes']:
                query.append('AND {0} && %({0})s'.format(field))
                qvars[field] = value
            elif field.startswith('attributes.'):
                field = field.replace('attributes.', '')
                query.append('AND attributes @> %(attr_{})s'.format(field))
                qvars['attr_' + field] = {field: value[0]}
            elif len(value) == 1:
                value = value[0]
                if field.endswith('!'):
                    if value.startswith('~'):
                        query.append('AND NOT "{0}" ILIKE %(not_{0})s'.format(field[:-1]))
                        qvars['not_' + field[:-1]] = '%' + value[1:] + '%'
                    else:
                        query.append('AND "{0}"!=%(not_{0})s'.format(field[:-1]))
                        qvars['not_' + field[:-1]] = value
                else:
                    if value.startswith('~'):
                        query.append('AND "{0}" ILIKE %({0})s'.format(field))
                        qvars[field] = '%' + value[1:] + '%'
                    else:
                        query.append('AND "{0}"=%({0})s'.format(field))
                        qvars[field] = value
            else:
                if field.endswith('!'):
                    if '~' in [v[0] for v in value]:
                        query.append('AND "{0}" !~* (%(not_regex_{0})s)'.format(field[:-1]))
                        qvars['not_regex_' + field[:-1]] = '|'.join([v.lstrip('~') for v in value])
                    else:
                        query.append('AND NOT "{0}"=ANY(%(not_{0})s)'.format(field[:-1]))
                        qvars['not_' + field[:-1]] = value
                else:
                    if '~' in [v[0] for v in value]:
                        query.append('AND "{0}" ~* (%(regex_{0})s)'.format(field))
                        qvars['regex_' + field] = '|'.join([v.lstrip('~') for v in value])
                    else:
                        query.append('AND "{0}"=ANY(%({0})s)'.format(field))
                        qvars[field] = value

        return Query(where='\n'.join(query), vars=qvars, sort=','.join(sort), group=group)

    @staticmethod
    def from_dict(d, query_time=None):
        return QueryBuilderImpl.from_params(MultiDict(d), query_time)

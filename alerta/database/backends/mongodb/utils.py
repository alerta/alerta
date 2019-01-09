import json
import re
from collections import namedtuple

import pytz
from pyparsing import ParseException
from werkzeug.datastructures import MultiDict

from alerta.database.base import QueryBuilder
from alerta.exceptions import ApiError
from alerta.utils.format import DateTime

from .queryparser import QueryParser

Query = namedtuple('Query', ['where', 'sort', 'group'])
Query.__new__.__defaults__ = ({}, {}, 'lastReceiveTime', 'status')  # type: ignore


class QueryBuilderImpl(QueryBuilder):

    @staticmethod
    def from_params(params: MultiDict, customers=None, query_time=None):

        # q
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

        # customers
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

        # sort-by
        sort = list()
        direction = 1
        if params.get('reverse', None):
            direction = -1
        if params.get('sort-by', None):
            for sort_by in params.getlist('sort-by'):
                if sort_by in ['createTime', 'receiveTime', 'lastReceiveTime']:
                    sort.append((sort_by, -direction))  # reverse chronological
                else:
                    sort.append((sort_by, direction))
        else:
            sort.append(('lastReceiveTime', -direction))

        # group-by
        group = params.getlist('group-by')

        # id
        ids = params.getlist('id')
        if len(ids) == 1:
            query['$or'] = [{'_id': {'$regex': '^' + ids[0]}}, {'lastReceiveId': {'$regex': '^' + ids[0]}}]
        elif ids:
            query['$or'] = [{'_id': {'$regex': re.compile('|'.join(['^' + i for i in ids]))}},
                            {'lastReceiveId': {'$regex': re.compile('|'.join(['^' + i for i in ids]))}}]

        EXCLUDE_QUERY = ['_', 'callback', 'token', 'api-key', 'q', 'q.df', 'q.op', 'id',
                         'from-date', 'to-date', 'duplicateCount', 'repeat', 'sort-by',
                         'reverse', 'group-by', 'page', 'page-size', 'limit']
        # fields
        for field in params:
            if field in EXCLUDE_QUERY:
                continue
            value = params.getlist(field)
            if len(value) == 1:
                value = value[0]
                if field.endswith('!'):
                    if value.startswith('~'):
                        query[field[:-1]] = dict()
                        query[field[:-1]]['$not'] = re.compile(value[1:], re.IGNORECASE)
                    else:
                        query[field[:-1]] = dict()
                        query[field[:-1]]['$ne'] = value
                else:
                    if value.startswith('~'):
                        query[field] = dict()
                        query[field]['$regex'] = re.compile(value[1:], re.IGNORECASE)
                    else:
                        query[field] = value
            else:
                if field.endswith('!'):
                    if '~' in [v[0] for v in value]:
                        value = '|'.join([v.lstrip('~') for v in value])
                        query[field[:-1]] = dict()
                        query[field[:-1]]['$not'] = re.compile(value, re.IGNORECASE)
                    else:
                        query[field[:-1]] = dict()
                        query[field[:-1]]['$nin'] = value
                else:
                    if '~' in [v[0] for v in value]:
                        value = '|'.join([v.lstrip('~') for v in value])
                        query[field] = dict()
                        query[field]['$regex'] = re.compile(value, re.IGNORECASE)
                    else:
                        query[field] = dict()
                        query[field]['$in'] = value

        if customer_query:
            query = {'$and': [customer_query, query]}

        return Query(where=query, sort=sort, group=group)

    @staticmethod
    def from_dict(d, query_time=None):
        return QueryBuilderImpl.from_params(MultiDict(d), query_time)

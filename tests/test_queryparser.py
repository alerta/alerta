import unittest


def skip_postgres():
    try:
        import psycopg2  # noqa
    except ImportError:
        return True
    return False


class PostgresQueryTestCase(unittest.TestCase):

    def setUp(self):

        if skip_postgres():
            self.skipTest('psycopg2 import failed')
        from alerta.database.backends.postgres.queryparser import \
            QueryParser as PostgresQueryParser
        self.parser = PostgresQueryParser()

    def test_word_and_phrase_terms(self):

        # default field (ie. "text") contains word
        string = r'''quick'''
        sql, params = self.parser.parse(string)
        self.assertEqual(sql, '"text" ILIKE %(_qp_0)s')
        self.assertEqual(params, {'_qp_0': '%quick%'})

        # default field (ie. "text") contains either words
        string = r'''quick OR brown'''
        sql, params = self.parser.parse(string)
        self.assertEqual(sql, '("text" ILIKE %(_qp_0)s OR "text" ILIKE %(_qp_1)s)')
        self.assertEqual(params, {'_qp_0': '%quick%', '_qp_1': '%brown%'})

        # default field (ie. "text") contains either words (default operator)
        string = r'''quick brown'''
        sql, params = self.parser.parse(string)
        self.assertEqual(sql, '("text" ILIKE %(_qp_0)s OR "text" ILIKE %(_qp_1)s)')
        self.assertEqual(params, {'_qp_0': '%quick%', '_qp_1': '%brown%'})

        # default field (ie. "text") contains exact phrase
        string = r'''"quick brown"'''
        sql, params = self.parser.parse(string)
        self.assertEqual(sql, '"text" ~* %(_qp_0)s')
        self.assertEqual(params, {'_qp_0': '\\yquick brown\\y'})

    def test_field_names(self):

        # field contains word
        string = r'''status:active'''
        sql, params = self.parser.parse(string)
        self.assertEqual(sql, '"status" ILIKE %(_qp_0)s')
        self.assertEqual(params, {'_qp_0': '%active%'})

        # field contains either words
        string = r'''title:(quick OR brown)'''
        sql, params = self.parser.parse(string)
        self.assertEqual(sql, '("title" ILIKE %(_qp_0)s OR "title" ILIKE %(_qp_1)s)')
        self.assertEqual(params, {'_qp_0': '%quick%', '_qp_1': '%brown%'})

        # field contains either words (default operator)
        string = r'''title:(quick brown)'''
        sql, params = self.parser.parse(string)
        self.assertEqual(sql, '("title" ILIKE %(_qp_0)s OR "title" ILIKE %(_qp_1)s)')
        self.assertEqual(params, {'_qp_0': '%quick%', '_qp_1': '%brown%'})

        # field contains exact phrase
        string = r'''author:"John Smith"'''
        sql, params = self.parser.parse(string)
        self.assertEqual(sql, '"author" ~* %(_qp_0)s')
        self.assertEqual(params, {'_qp_0': '\\yJohn Smith\\y'})

        # # any attribute contains word or phrase
        # string = r'''attributes.\*:(quick brown)'''
        # sql, params = self.parser.parse(string)
        # self.assertEqual(sql, '??')

        # attribute field has non-null value
        string = r'''_exists_:title'''
        sql, params = self.parser.parse(string)
        self.assertEqual(sql, '"attributes"::jsonb ? %(_qp_0)s')
        self.assertEqual(params, {'_qp_0': 'title'})

        # attribute contains word
        string = r'''foo.vendor:cisco'''
        sql, params = self.parser.parse(string)
        self.assertEqual(sql, '"foo"::jsonb ->>%(_qp_0)s ILIKE %(_qp_1)s')
        self.assertEqual(params, {'_qp_0': 'vendor', '_qp_1': '%cisco%'})

        # attribute contains word ("_" shortcut)
        string = r'''_.vendor:cisco'''
        sql, params = self.parser.parse(string)
        self.assertEqual(sql, '"attributes"::jsonb ->>%(_qp_0)s ILIKE %(_qp_1)s')
        self.assertEqual(params, {'_qp_0': 'vendor', '_qp_1': '%cisco%'})

        # attribute contains either words
        string = r'''attributes.vendor:(cisco OR juniper)'''
        sql, params = self.parser.parse(string)
        self.assertEqual(sql, '("attributes"::jsonb ->>%(_qp_2)s ILIKE %(_qp_0)s OR "attributes"::jsonb ->>%(_qp_2)s ILIKE %(_qp_1)s)')
        self.assertEqual(params, {'_qp_0': '%cisco%', '_qp_1': '%juniper%', '_qp_2': 'vendor'})

        # attribute contains either words (default operator)
        string = r'''attributes.vendor:(cisco juniper)'''
        sql, params = self.parser.parse(string)
        self.assertEqual(sql, '("attributes"::jsonb ->>%(_qp_2)s ILIKE %(_qp_0)s OR "attributes"::jsonb ->>%(_qp_2)s ILIKE %(_qp_1)s)')
        self.assertEqual(params, {'_qp_0': '%cisco%', '_qp_1': '%juniper%', '_qp_2': 'vendor'})

        # attribute contains either words ("_" shortcut, default operator)
        string = r'''_.vendor:(cisco juniper)'''
        sql, params = self.parser.parse(string)
        self.assertEqual(sql, '("attributes"::jsonb ->>%(_qp_2)s ILIKE %(_qp_0)s OR "attributes"::jsonb ->>%(_qp_2)s ILIKE %(_qp_1)s)')
        self.assertEqual(params, {'_qp_0': '%cisco%', '_qp_1': '%juniper%', '_qp_2': 'vendor'})

        # attribute contains exact phrase
        string = r'''foo.vendor:"quick brown"'''
        sql, params = self.parser.parse(string)
        self.assertEqual(sql, '"foo"::jsonb ->>%(_qp_0)s ~* %(_qp_1)s')
        self.assertEqual(params, {'_qp_0': 'vendor', '_qp_1': '\\yquick brown\\y'})

        # attribute contains exact phrase ("_" shortcut)
        string = r'''_.vendor:"quick brown"'''
        sql, params = self.parser.parse(string)
        self.assertEqual(sql, '"attributes"::jsonb ->>%(_qp_0)s ~* %(_qp_1)s')
        self.assertEqual(params, {'_qp_0': 'vendor', '_qp_1': '\\yquick brown\\y'})

    def test_wildcards(self):

        # ? = single character, * = one or more characters
        string = r'''text:qu?ck bro*'''
        sql, params = self.parser.parse(string)
        self.assertEqual(sql, '("text" ~* %(_qp_0)s OR "text" ~* %(_qp_1)s)')
        self.assertEqual(params, {'_qp_0': '\\yqu.?ck\\y', '_qp_1': '\\ybro.*\\y'})

    def test_regular_expressions(self):

        string = r'''name:/joh?n(ath[oa]n)/'''
        sql, params = self.parser.parse(string)
        self.assertEqual(sql, '"name" ~* %(_qp_0)s')
        self.assertEqual(params, {'_qp_0': 'joh?n(ath[oa]n)'})

    def test_fuzziness(self):
        pass

    def test_proximity_searches(self):
        pass

    def test_ranges(self):

        string = r'''date:[2012-01-01 TO 2012-12-31]'''
        sql, params = self.parser.parse(string)
        self.assertEqual(sql, '("date" >= %(_qp_0)s AND "date" <= %(_qp_1)s)')
        self.assertEqual(params, {'_qp_0': '2012-01-01', '_qp_1': '2012-12-31'})

        string = r'''count:[1 TO 5]'''
        sql, params = self.parser.parse(string)
        self.assertEqual(sql, '("count" >= %(_qp_0)s AND "count" <= %(_qp_1)s)')
        self.assertEqual(params, {'_qp_0': '1', '_qp_1': '5'})

        string = r'''tag:{alpha TO omega}'''
        sql, params = self.parser.parse(string)
        self.assertEqual(sql, '("tag" > %(_qp_0)s AND "tag" < %(_qp_1)s)')
        self.assertEqual(params, {'_qp_0': 'alpha', '_qp_1': 'omega'})

        string = r'''count:[10 TO *]'''
        sql, params = self.parser.parse(string)
        self.assertEqual(sql, '("count" >= %(_qp_0)s AND 1=1)')
        self.assertEqual(params, {'_qp_0': '10'})

        string = r'''date:{* TO 2012-01-01}'''
        sql, params = self.parser.parse(string)
        self.assertEqual(sql, '(1=1 AND "date" < %(_qp_0)s)')
        self.assertEqual(params, {'_qp_0': '2012-01-01'})

        string = r'''count:[1 TO 5}'''
        sql, params = self.parser.parse(string)
        self.assertEqual(sql, '("count" >= %(_qp_0)s AND "count" < %(_qp_1)s)')
        self.assertEqual(params, {'_qp_0': '1', '_qp_1': '5'})

    def test_unbounded_ranges(self):

        string = r'''age:>10'''
        sql, params = self.parser.parse(string)
        self.assertEqual(sql, '("age" > %(_qp_0)s)')
        self.assertEqual(params, {'_qp_0': '10'})

        string = r'''age:>=10'''
        sql, params = self.parser.parse(string)
        self.assertEqual(sql, '("age" >= %(_qp_0)s)')
        self.assertEqual(params, {'_qp_0': '10'})

        string = r'''age:<10'''
        sql, params = self.parser.parse(string)
        self.assertEqual(sql, '("age" < %(_qp_0)s)')
        self.assertEqual(params, {'_qp_0': '10'})

        string = r'''age:<=10'''
        sql, params = self.parser.parse(string)
        self.assertEqual(sql, '("age" <= %(_qp_0)s)')
        self.assertEqual(params, {'_qp_0': '10'})

    def test_boosting(self):
        pass

    def test_boolean_operators(self):

        # OR (||)
        string = r'''"jakarta apache" jakarta'''
        sql, params = self.parser.parse(string)
        self.assertEqual(sql, '("text" ~* %(_qp_0)s OR "text" ILIKE %(_qp_1)s)')
        self.assertEqual(params, {'_qp_0': '\\yjakarta apache\\y', '_qp_1': '%jakarta%'})

        string = r'''"jakarta apache" OR jakarta'''
        sql, params = self.parser.parse(string)
        self.assertEqual(sql, '("text" ~* %(_qp_0)s OR "text" ILIKE %(_qp_1)s)')
        self.assertEqual(params, {'_qp_0': '\\yjakarta apache\\y', '_qp_1': '%jakarta%'})

        string = r'''"jakarta apache" || jakarta'''
        sql, params = self.parser.parse(string)
        self.assertEqual(sql, '("text" ~* %(_qp_0)s OR "text" ILIKE %(_qp_1)s)')
        self.assertEqual(params, {'_qp_0': '\\yjakarta apache\\y', '_qp_1': '%jakarta%'})

        # AND (&&)
        string = r'''"jakarta apache" AND "Apache Lucene"'''
        sql, params = self.parser.parse(string)
        self.assertEqual(sql, '("text" ~* %(_qp_0)s AND "text" ~* %(_qp_1)s)')
        self.assertEqual(params, {'_qp_0': '\\yjakarta apache\\y', '_qp_1': '\\yApache Lucene\\y'})

        string = r'''"jakarta apache" && "Apache Lucene"'''
        sql, params = self.parser.parse(string)
        self.assertEqual(sql, '("text" ~* %(_qp_0)s AND "text" ~* %(_qp_1)s)')
        self.assertEqual(params, {'_qp_0': '\\yjakarta apache\\y', '_qp_1': '\\yApache Lucene\\y'})

        # + (required)
        pass

        # NOT (!)
        string = r'''"jakarta apache" NOT "Apache Lucene"'''
        sql, params = self.parser.parse(string)
        self.assertEqual(sql, '("text" ~* %(_qp_0)s AND NOT ("text" ~* %(_qp_1)s))')
        self.assertEqual(params, {'_qp_0': '\\yjakarta apache\\y', '_qp_1': '\\yApache Lucene\\y'})

        string = r'''"jakarta apache" !"Apache Lucene"'''
        sql, params = self.parser.parse(string)
        self.assertEqual(sql, '("text" ~* %(_qp_0)s AND NOT ("text" ~* %(_qp_1)s))')
        self.assertEqual(params, {'_qp_0': '\\yjakarta apache\\y', '_qp_1': '\\yApache Lucene\\y'})

        string = r'''NOT "jakarta apache"'''
        sql, params = self.parser.parse(string)
        self.assertEqual(sql, 'NOT ("text" ~* %(_qp_0)s)')
        self.assertEqual(params, {'_qp_0': '\\yjakarta apache\\y'})

        string = r'''group:"jakarta apache" NOT group:"Apache Lucene"'''
        sql, params = self.parser.parse(string)
        self.assertEqual(sql, '("group" ~* %(_qp_0)s AND NOT ("group" ~* %(_qp_1)s))')
        self.assertEqual(params, {'_qp_0': '\\yjakarta apache\\y', '_qp_1': '\\yApache Lucene\\y'})

        # - (prohibit)
        pass

    def test_grouping(self):

        # field exact match
        string = r'''(quick OR brown) AND fox'''
        sql, params = self.parser.parse(string)
        self.assertEqual(sql, '(("text" ILIKE %(_qp_0)s OR "text" ILIKE %(_qp_1)s) AND "text" ILIKE %(_qp_2)s)')
        self.assertEqual(params, {'_qp_0': '%quick%', '_qp_1': '%brown%', '_qp_2': '%fox%'})

        # field exact match
        string = r'''status:(active OR pending) title:(full text search)'''
        sql, params = self.parser.parse(string)
        self.assertEqual(
            sql, '(("status" ILIKE %(_qp_0)s OR "status" ILIKE %(_qp_1)s) OR ("title" ILIKE %(_qp_2)s OR "title" ILIKE %(_qp_3)s))')
        self.assertEqual(params, {'_qp_0': '%active%', '_qp_1': '%pending%', '_qp_2': '%full%', '_qp_3': '%text%'})

    def test_sql_injection_prevention(self):

        # single quotes in search terms should be safely parameterized
        string = r'''text:O'Brien'''
        sql, params = self.parser.parse(string)
        self.assertEqual(sql, '"text" ILIKE %(_qp_0)s')
        self.assertIn("O'Brien", params['_qp_0'])

        # SQL keywords in search terms should be safely parameterized
        string = '''"DROP TABLE alerts"'''
        sql, params = self.parser.parse(string)
        self.assertEqual(sql, '"text" ~* %(_qp_0)s')
        self.assertIn('DROP TABLE alerts', params['_qp_0'])

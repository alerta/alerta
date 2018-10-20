import unittest

from alerta.database.backends.postgres.queryparser import QueryParser


class PostgresQueryTestCase(unittest.TestCase):

    def setUp(self):

        self.parser = QueryParser()

    def test_word_and_phrase_terms(self):

        # default field (ie. "text") contains word
        string = r'''quick'''
        r = self.parser.parse(string)
        self.assertEqual(r, '"text" ILIKE \'%%quick%%\'')

        # default field (ie. "text") contains phrase
        string = r'''"quick brown"'''
        r = self.parser.parse(string)
        self.assertEqual(r, '"text" ~* \'quick brown\'')

    def test_field_names(self):

        # field contains word
        string = r'''status:active'''
        r = self.parser.parse(string)
        self.assertEqual(r, '"status" ILIKE \'%%active%%\'')

        # field contains either words
        string = r'''title:(quick OR brown)'''
        r = self.parser.parse(string)
        self.assertEqual(r, '("title" ILIKE \'%%quick%%\' OR "title" ILIKE \'%%brown%%\')')

        # field contains either words (default operator)
        string = r'''title:(quick brown)'''
        r = self.parser.parse(string)
        self.assertEqual(r, '("title" ILIKE \'%%quick%%\' OR "title" ILIKE \'%%brown%%\')')

        # field exact match
        string = r'''author:"John Smith"'''
        r = self.parser.parse(string)
        self.assertEqual(r, '"author"=\'John Smith\'')

        # # any attribute contains word or phrase
        # string = r'''attributes.\*:(quick brown)'''
        # r = self.parser.parse(string)
        # self.assertEqual(r, '??')

        # attribute field has non-null value
        string = r'''_exists_:title'''
        r = self.parser.parse(string)
        self.assertEqual(r, '"attributes"::jsonb ? \'title\'')

    def test_wildcards(self):

        # ? = single character, * = one or more characters
        string = r'''text:qu?ck bro*'''
        r = self.parser.parse(string)
        self.assertEqual(r, '"text" ~* \'qu.?ck bro.*\'')

    def test_regular_expressions(self):

        string = r'''name:/joh?n(ath[oa]n)/'''
        r = self.parser.parse(string)
        self.assertEqual(r, '"name" ~* \'joh?n(ath[oa]n)\'')

    def test_fuzziness(self):
        pass

    def test_proximity_searches(self):
        pass

    def test_ranges(self):

        string = r'''date:[2012-01-01 TO 2012-12-31]'''
        r = self.parser.parse(string)
        self.assertEqual(r, '("date" >= \'2012-01-01\' AND "date" <= \'2012-12-31\')')

        string = r'''count:[1 TO 5]'''
        r = self.parser.parse(string)
        self.assertEqual(r, '("count" >= \'1\' AND "count" <= \'5\')')

        string = r'''tag:{alpha TO omega}'''
        r = self.parser.parse(string)
        self.assertEqual(r, '("tag" > \'alpha\' AND "tag" < \'omega\')')

        string = r'''count:[10 TO *]'''
        r = self.parser.parse(string)
        self.assertEqual(r, '("count" >= \'10\' AND 1=1)')

        string = r'''date:{* TO 2012-01-01}'''
        r = self.parser.parse(string)
        self.assertEqual(r, '(1=1 AND "date" < \'2012-01-01\')')

        string = r'''count:[1 TO 5}'''
        r = self.parser.parse(string)
        self.assertEqual(r, '("count" >= \'1\' AND "count" < \'5\')')

    def test_unbounded_ranges(self):

        string = r'''age:>10'''
        r = self.parser.parse(string)
        self.assertEqual(r, '("age" > \'10\')')

        string = r'''age:>=10'''
        r = self.parser.parse(string)
        self.assertEqual(r, '("age" >= \'10\')')

        string = r'''age:<10'''
        r = self.parser.parse(string)
        self.assertEqual(r, '("age" < \'10\')')

        string = r'''age:<=10'''
        r = self.parser.parse(string)
        self.assertEqual(r, '("age" <= \'10\')')

    def test_boosting(self):
        pass

    def test_boolean_operators(self):
        pass

    def test_grouping(self):

        # field exact match
        string = r'''(quick OR brown) AND fox'''
        r = self.parser.parse(string)
        self.assertEqual(r, '(("text" ILIKE \'%%quick%%\' OR "text" ILIKE \'%%brown%%\') AND "text" ILIKE \'%%fox%%\')')

        # field exact match
        string = r'''status:(active OR pending) title:(full text search)'''
        r = self.parser.parse(string)
        self.assertEqual(
            r, '(("status" ILIKE \'%%active%%\' OR "status" ILIKE \'%%pending%%\') OR ("title" ILIKE \'%%full%%\' OR "title" ILIKE \'%%text%%\'))')

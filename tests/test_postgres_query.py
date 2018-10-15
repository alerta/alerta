import unittest

from alerta.app import create_app
from alerta.database.backends.postgres.parser import expression as postgres_search


class PostgresQueryTestCase(unittest.TestCase):

    def setUp(self):

        test_config = {
            'TESTING': True
        }
        self.app = create_app(test_config)

    def test_word_and_phrase_terms(self):

        with self.app.test_request_context('/'):

            # default field (ie. "text") contains word
            string = r'''quick'''
            r = postgres_search.parseString(string)
            self.assertEqual(repr(r[0]), '"text" ILIKE \'%%quick%%\'')

            # default field (ie. "text") contains phrase
            string = r'''"quick brown"'''
            r = postgres_search.parseString(string)
            self.assertEqual(repr(r[0]), '"text" ~* \'quick brown\'')

    def test_field_names(self):

        with self.app.test_request_context('/'):

            # field contains word
            string = r'''status:active'''
            r = postgres_search.parseString(string)
            self.assertEqual(repr(r[0]), '"status" ILIKE \'%%active%%\'')

            # # field contains either words
            # string = r'''title:(quick OR brown)'''
            # r = postgres_search.parseString(string)
            # self.assertEqual(repr(r[0]), '', repr(r[0]))

            # # field contains either words (default operator)
            # string = r'''title:(quick brown)'''
            # r = postgres_search.parseString(string)
            # self.assertEqual(repr(r[0]), '')

            # field exact match
            string = r'''author:"John Smith"'''
            r = postgres_search.parseString(string)
            self.assertEqual(repr(r[0]), '"author"=\'John Smith\'')

            # # any attribute contains word or phrase
            # string = r'''attributes.\*:(quick brown)'''
            # r = postgres_search.parseString(string)
            # self.assertEqual(repr(r[0]), '??')

            # attribute field has non-null value
            string = r'''_exists_:title'''
            r = postgres_search.parseString(string)
            self.assertEqual(repr(r[0]), '"attributes"::jsonb ? \'title\'')

    def test_wildcards(self):

        with self.app.test_request_context('/'):

            # ? = single character, * = one or more characters
            string = r'''text:qu?ck bro*'''
            r = postgres_search.parseString(string)
            self.assertEqual(repr(r[0]), '"text" ~* \'qu.?ck bro.*\'')

    def test_regular_expressions(self):

        with self.app.test_request_context('/'):

            string = r'''name:/joh?n(ath[oa]n)/'''
            r = postgres_search.parseString(string)
            self.assertEqual(repr(r[0]), '"name" ~* \'joh?n(ath[oa]n)\'')

    def test_fuzziness(self):
        pass

    def test_proximity_searches(self):
        pass

    # def test_ranges(self):
    #
    #     string = r'''date:[2012-01-01 TO 2012-12-31]'''
    #     r = postgres_search.parseString(string)
    #     self.assertEqual(repr(r[0]), '??')
    #
    #     string = r'''count:[1 TO 5]'''
    #     r = postgres_search.parseString(string)
    #     self.assertEqual(repr(r[0]), '??')
    #
    #     string = r'''tag:{alpha TO omega}'''
    #     r = postgres_search.parseString(string)
    #     self.assertEqual(repr(r[0]), '??')
    #
    #     string = r'''count:[10 TO *]'''
    #     r = postgres_search.parseString(string)
    #     self.assertEqual(repr(r[0]), '??')
    #
    #     string = r''''date:{* TO 2012-01-01}'''
    #     r = postgres_search.parseString(string)
    #     self.assertEqual(repr(r[0]), '??')
    #
    #     string = r''''count:[1 TO 5}'''
    #     r = postgres_search.parseString(string)
    #     self.assertEqual(repr(r[0]), '??')
    #
    # def test_unbounded_ranges(self):
    #
    #     string = r'''age:>10'''
    #     r = postgres_search.parseString(string)
    #     self.assertEqual(repr(r[0]), '??')
    #
    #     string = r'''age:>=10'''
    #     r = postgres_search.parseString(string)
    #     self.assertEqual(repr(r[0]), '??')
    #
    #     string = r'''age:<10'''
    #     r = postgres_search.parseString(string)
    #     self.assertEqual(repr(r[0]), '??')
    #
    #     string = r'''age:<=10'''
    #     r = postgres_search.parseString(string)
    #     self.assertEqual(repr(r[0]), '??')

    def test_boosting(self):
        pass

    def test_boolean_operators(self):
        pass

    # def test_grouping(self):
    #
    #     # field exact match
    #     string = r'''(quick OR brown) AND fox'''
    #     r = postgres_search.parseString(string)
    #     self.assertEqual(repr(r[0]), '??')
    #
    #     # field exact match
    #     string = r'''status:(active OR pending) title:(full text search)'''
    #     r = postgres_search.parseString(string)
    #     self.assertEqual(repr(r[0]), '??')

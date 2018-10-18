import unittest

from alerta.database.backends.mongodb.parser import expression as mongo_search


class MongoQueryTestCase(unittest.TestCase):

    def setUp(self):
        pass

    def test_word_and_phrase_terms(self):

        # default field (ie. "text") contains word
        string = r'''quick'''
        r = mongo_search.parseString(string)
        self.assertEqual(repr(r[0]), '{ "$text": { "$search": "quick" } }')

        # default field (ie. "text") contains phrase
        string = r'''"quick brown"'''
        r = mongo_search.parseString(string)
        self.assertEqual(repr(r[0]), '{ "$text": { "$search": "\\"quick brown\\"" } }')

    def test_field_names(self):

        # field contains word
        string = r'''status:active'''
        r = mongo_search.parseString(string)
        self.assertEqual(repr(r[0]), '{ "status": { "$regex": "active" } }')

        # # field contains either words
        # string = r'''title:(quick OR brown)'''
        # r = mongo_search.parseString(string)
        # self.assertEqual(repr(r[0]), '{ "title": { "$or": [ { "$regex": { "quick" } }, { "$regex": { "brown" } } ] } }', repr(r[0]))

        # # field contains either words (default operator)
        # string = r'''title:(quick brown)'''
        # r = mongo_search.parseString(string)
        # self.assertEqual(repr(r[0]), '{ "status": { "$regex": "active" } }')

        # field exact match
        string = r'''author:"John Smith"'''
        r = mongo_search.parseString(string)
        self.assertEqual(repr(r[0]), '{ "author": "John Smith" }')

        # # any attribute contains word or phrase
        # string = r'''attributes.\*:(quick brown)'''
        # r = mongo_search.parseString(string)
        # self.assertEqual(repr(r[0]), '??')

        # attribute field has non-null value
        string = r'''_exists_:title'''
        r = mongo_search.parseString(string)
        self.assertEqual(repr(r[0]), '{ "attributes.title": { "$exists": true } }')

    def test_wildcards(self):

        # ? = single character, * = one or more characters
        string = r'''text:qu?ck bro*'''
        r = mongo_search.parseString(string)
        self.assertEqual(repr(r[0]), '{ "text": { "$regex": "qu.?ck bro.*" } }')

    def test_regular_expressions(self):

        string = r'''name:/joh?n(ath[oa]n)/'''
        r = mongo_search.parseString(string)
        self.assertEqual(repr(r[0]), '{ "name": { "$regex": "joh?n(ath[oa]n)" } }')

    def test_fuzziness(self):
        pass

    def test_proximity_searches(self):
        pass

    # def test_ranges(self):
    #
    #     string = r'''date:[2012-01-01 TO 2012-12-31]'''
    #     r = mongo_search.parseString(string)
    #     self.assertEqual(repr(r[0]), '??')
    #
    #     string = r'''count:[1 TO 5]'''
    #     r = mongo_search.parseString(string)
    #     self.assertEqual(repr(r[0]), '??')
    #
    #     string = r'''tag:{alpha TO omega}'''
    #     r = mongo_search.parseString(string)
    #     self.assertEqual(repr(r[0]), '??')
    #
    #     string = r'''count:[10 TO *]'''
    #     r = mongo_search.parseString(string)
    #     self.assertEqual(repr(r[0]), '??')
    #
    #     string = r''''date:{* TO 2012-01-01}'''
    #     r = mongo_search.parseString(string)
    #     self.assertEqual(repr(r[0]), '??')
    #
    #     string = r''''count:[1 TO 5}'''
    #     r = mongo_search.parseString(string)
    #     self.assertEqual(repr(r[0]), '??')
    #
    # def test_unbounded_ranges(self):
    #
    #     string = r'''age:>10'''
    #     r = mongo_search.parseString(string)
    #     self.assertEqual(repr(r[0]), '??')
    #
    #     string = r'''age:>=10'''
    #     r = mongo_search.parseString(string)
    #     self.assertEqual(repr(r[0]), '??')
    #
    #     string = r'''age:<10'''
    #     r = mongo_search.parseString(string)
    #     self.assertEqual(repr(r[0]), '??')
    #
    #     string = r'''age:<=10'''
    #     r = mongo_search.parseString(string)
    #     self.assertEqual(repr(r[0]), '??')

    def test_boosting(self):
        pass

    def test_boolean_operators(self):
        pass

    # def test_grouping(self):
    #
    #     # field exact match
    #     string = r'''(quick OR brown) AND fox'''
    #     r = mongo_search.parseString(string)
    #     self.assertEqual(repr(r[0]), '??')
    #
    #     # field exact match
    #     string = r'''status:(active OR pending) title:(full text search)'''
    #     r = mongo_search.parseString(string)
    #     self.assertEqual(repr(r[0]), '??')


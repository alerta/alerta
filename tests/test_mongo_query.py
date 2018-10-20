import unittest

from alerta.database.backends.mongodb.queryparser import QueryParser


class MongoQueryTestCase(unittest.TestCase):

    def setUp(self):

        self.parser = QueryParser()

    def test_word_and_phrase_terms(self):

        # default field (ie. "text") contains word
        string = r'''quick'''
        r = self.parser.parse(string)
        self.assertEqual(r, '{ "text": { "$regex": "quick" } }')

        # default field (ie. "text") contains phrase
        string = r'''"quick brown"'''
        r = self.parser.parse(string)
        self.assertEqual(r, '{ "text": { "$regex": "\\"quick brown\\"" } }')

    def test_field_names(self):

        # field contains word
        string = r'''status:active'''
        r = self.parser.parse(string)
        self.assertEqual(r, '{ "status": { "$regex": "active" } }')

        # field contains either words
        string = r'''title:(quick OR brown)'''
        r = self.parser.parse(string)
        self.assertEqual(r, '{ "$or": [{ "title": { "$regex": "quick" } }, { "title": { "$regex": "brown" } }] }')

        # field contains either words (default operator)
        string = r'''title:(quick brown)'''
        r = self.parser.parse(string)
        self.assertEqual(r, '{ "$or": [{ "title": { "$regex": "quick" } }, { "title": { "$regex": "brown" } }] }')

        # field exact match
        string = r'''author:"John Smith"'''
        r = self.parser.parse(string)
        self.assertEqual(r, '{ "author": "John Smith" }')

        # # # any attribute contains word or phrase
        # # string = r'''attributes.\*:(quick brown)'''
        # # r = self.parser.parse(string)
        # # self.assertEqual(r, '??')

        # attribute field has non-null value
        string = r'''_exists_:title'''
        r = self.parser.parse(string)
        self.assertEqual(r, '{ "attributes.title": { "$exists": true } }')

    def test_wildcards(self):

        # ? = single character, * = one or more characters
        string = r'''text:qu?ck bro*'''
        r = self.parser.parse(string)
        self.assertEqual(r, '{ "text": { "$regex": "qu.?ck bro.*" } }')

    def test_regular_expressions(self):

        string = r'''name:/joh?n(ath[oa]n)/'''
        r = self.parser.parse(string)
        self.assertEqual(r, '{ "name": { "$regex": "joh?n(ath[oa]n)" } }')

    def test_fuzziness(self):
        pass

    def test_proximity_searches(self):
        pass

    def test_ranges(self):

        string = r'''date:[2012-01-01 TO 2012-12-31]'''
        r = self.parser.parse(string)
        self.assertEqual(
            r, '{ "$and": [ { "date": { "$gte": "2012-01-01" } }, { "date": { "$lte": "2012-12-31" } } ] }')

        string = r'''count:[1 TO 5]'''
        r = self.parser.parse(string)
        self.assertEqual(r, '{ "$and": [ { "count": { "$gte": "1" } }, { "count": { "$lte": "5" } } ] }')

        string = r'''tag:{alpha TO omega}'''
        r = self.parser.parse(string)
        self.assertEqual(r, '{ "$and": [ { "tag": { "$gt": "alpha" } }, { "tag": { "$lt": "omega" } } ] }')

        string = r'''count:[10 TO *]'''
        r = self.parser.parse(string)
        self.assertEqual(r, '{ "$and": [ { "count": { "$gte": "10" } }, {} ] }')

        string = r'''date:{* TO 2012-01-01}'''
        r = self.parser.parse(string)
        self.assertEqual(r, '{ "$and": [ {{}}, { "date": { "$lt": "2012-01-01" } } ] }')

        string = r'''count:[1 TO 5}'''
        r = self.parser.parse(string)
        self.assertEqual(r, '{ "$and": [ { "count": { "$gte": "1" } }, { "count": { "$lt": "5" } } ] }')

    def test_unbounded_ranges(self):

        string = r'''age:>10'''
        r = self.parser.parse(string)
        self.assertEqual(r, '{ "age": { "$gt": "10" } }')

        string = r'''age:>=10'''
        r = self.parser.parse(string)
        self.assertEqual(r, '{ "age": { "$gte": "10" } }')

        string = r'''age:<10'''
        r = self.parser.parse(string)
        self.assertEqual(r, '{ "age": { "$lt": "10" } }')

        string = r'''age:<=10'''
        r = self.parser.parse(string)
        self.assertEqual(r, '{ "age": { "$lte": "10" } }')

    def test_boosting(self):
        pass

    def test_boolean_operators(self):
        pass

    def test_grouping(self):

        # field exact match
        string = r'''(quick OR brown) AND fox'''
        r = self.parser.parse(string)
        self.assertEqual(
            r, '{ "$and": [{ "$or": [{ "text": { "$regex": "quick" } }, { "text": { "$regex": "brown" } }] }, { "text": { "$regex": "fox" } }] }')

        # field exact match
        string = r'''status:(active OR pending) title:(full text search)'''
        r = self.parser.parse(string)
        self.assertEqual(
            r, '{ "$or": [{ "$or": [{ "status": { "$regex": "active" } }, { "status": { "$regex": "pending" } }] }, { "$or": [{ "title": { "$regex": "full" } }, { "title": { "$regex": "text" } }] }] }')

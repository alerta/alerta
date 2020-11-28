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
        r = self.parser.parse(string)
        self.assertEqual(r, '"text" ILIKE \'%%quick%%\'')

        # default field (ie. "text") contains either words
        string = r'''quick OR brown'''
        r = self.parser.parse(string)
        self.assertEqual(r, '("text" ILIKE \'%%quick%%\' OR "text" ILIKE \'%%brown%%\')')

        # default field (ie. "text") contains either words (default operator)
        string = r'''quick brown'''
        r = self.parser.parse(string)
        self.assertEqual(r, '("text" ILIKE \'%%quick%%\' OR "text" ILIKE \'%%brown%%\')')

        # default field (ie. "text") contains exact phrase
        string = r'''"quick brown"'''
        r = self.parser.parse(string)
        self.assertEqual(r, '"text" ~* \'\\yquick brown\\y\'')

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

        # field contains exact phrase
        string = r'''author:"John Smith"'''
        r = self.parser.parse(string)
        self.assertEqual(r, '"author" ~* \'\\yJohn Smith\\y\'')

        # # any attribute contains word or phrase
        # string = r'''attributes.\*:(quick brown)'''
        # r = self.parser.parse(string)
        # self.assertEqual(r, '??')

        # attribute field has non-null value
        string = r'''_exists_:title'''
        r = self.parser.parse(string)
        self.assertEqual(r, '"attributes"::jsonb ? \'title\'')

        # attribute contains word
        string = r'''foo.vendor:cisco'''
        r = self.parser.parse(string)
        self.assertEqual(r, '"foo"::jsonb ->>\'vendor\' ILIKE \'%%cisco%%\'')

        # attribute contains word ("_" shortcut)
        string = r'''_.vendor:cisco'''
        r = self.parser.parse(string)
        self.assertEqual(r, '"attributes"::jsonb ->>\'vendor\' ILIKE \'%%cisco%%\'')

        # attribute contains either words
        string = r'''attributes.vendor:(cisco OR juniper)'''
        r = self.parser.parse(string)
        self.assertEqual(r, '("attributes"::jsonb ->>\'vendor\' ILIKE \'%%cisco%%\' OR "attributes"::jsonb ->>\'vendor\' ILIKE \'%%juniper%%\')')

        # attribute contains either words (default operator)
        string = r'''attributes.vendor:(cisco juniper)'''
        r = self.parser.parse(string)
        self.assertEqual(r, '("attributes"::jsonb ->>\'vendor\' ILIKE \'%%cisco%%\' OR "attributes"::jsonb ->>\'vendor\' ILIKE \'%%juniper%%\')')

        # attribute contains either words ("_" shortcut, default operator)
        string = r'''_.vendor:(cisco juniper)'''
        r = self.parser.parse(string)
        self.assertEqual(r, '("attributes"::jsonb ->>\'vendor\' ILIKE \'%%cisco%%\' OR "attributes"::jsonb ->>\'vendor\' ILIKE \'%%juniper%%\')')

        # attribute contains exact phrase
        string = r'''foo.vendor:"quick brown"'''
        r = self.parser.parse(string)
        self.assertEqual(r, '"foo"::jsonb ->>\'vendor\' ~* \'\\yquick brown\\y\'')

        # attribute contains exact phrase ("_" shortcut)
        string = r'''_.vendor:"quick brown"'''
        r = self.parser.parse(string)
        self.assertEqual(r, '"attributes"::jsonb ->>\'vendor\' ~* \'\\yquick brown\\y\'')

    def test_wildcards(self):

        # ? = single character, * = one or more characters
        string = r'''text:qu?ck bro*'''
        r = self.parser.parse(string)
        self.assertEqual(r, '("text" ~* \'\\yqu.?ck\\y\' OR "text" ~* \'\\ybro.*\\y\')')

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

        # OR (||)
        string = r'''"jakarta apache" jakarta'''
        r = self.parser.parse(string)
        self.assertEqual(r, '("text" ~* \'\\yjakarta apache\\y\' OR "text" ILIKE \'%%jakarta%%\')')

        string = r'''"jakarta apache" OR jakarta'''
        r = self.parser.parse(string)
        self.assertEqual(r, '("text" ~* \'\\yjakarta apache\\y\' OR "text" ILIKE \'%%jakarta%%\')')

        string = r'''"jakarta apache" || jakarta'''
        r = self.parser.parse(string)
        self.assertEqual(r, '("text" ~* \'\\yjakarta apache\\y\' OR "text" ILIKE \'%%jakarta%%\')')

        # AND (&&)
        string = r'''"jakarta apache" AND "Apache Lucene"'''
        r = self.parser.parse(string)
        self.assertEqual(r, '("text" ~* \'\\yjakarta apache\\y\' AND "text" ~* \'\\yApache Lucene\\y\')')

        string = r'''"jakarta apache" && "Apache Lucene"'''
        r = self.parser.parse(string)
        self.assertEqual(r, '("text" ~* \'\\yjakarta apache\\y\' AND "text" ~* \'\\yApache Lucene\\y\')')

        # + (required)
        pass

        # NOT (!)
        string = r'''"jakarta apache" NOT "Apache Lucene"'''
        r = self.parser.parse(string)
        self.assertEqual(r, '("text" ~* \'\\yjakarta apache\\y\' AND NOT ("text" ~* \'\\yApache Lucene\\y\'))')

        string = r'''"jakarta apache" !"Apache Lucene"'''
        r = self.parser.parse(string)
        self.assertEqual(r, '("text" ~* \'\\yjakarta apache\\y\' AND NOT ("text" ~* \'\\yApache Lucene\\y\'))')

        string = r'''NOT "jakarta apache"'''
        r = self.parser.parse(string)
        self.assertEqual(r, 'NOT ("text" ~* \'\\yjakarta apache\\y\')')

        string = r'''group:"jakarta apache" NOT group:"Apache Lucene"'''
        r = self.parser.parse(string)
        self.assertEqual(r, '("group" ~* \'\\yjakarta apache\\y\' AND NOT ("group" ~* \'\\yApache Lucene\\y\'))')

        # - (prohibit)
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


def skip_mongodb():
    try:
        import pymongo  # noqa
    except ImportError:
        return True
    return False


class MongoQueryTestCase(unittest.TestCase):

    def setUp(self):

        if skip_mongodb():
            self.skipTest('pymongo import failed')
        from alerta.database.backends.mongodb.queryparser import \
            QueryParser as MongoQueryParser
        self.parser = MongoQueryParser()

    def test_word_and_phrase_terms(self):

        # default field (ie. "text") contains word
        string = r'''quick'''
        r = self.parser.parse(string)
        self.assertEqual(r, '{"text": {"$regex": "quick", "$options": "i"}}')

        # default field (ie. "text") contains either words
        string = r'''quick OR brown'''
        r = self.parser.parse(string)
        self.assertEqual(r, '{"$or": [{"text": {"$regex": "quick", "$options": "i"}}, {"text": {"$regex": "brown", "$options": "i"}}]}')

        # default field (ie. "text") contains either words (default operator)
        string = r'''quick brown'''
        r = self.parser.parse(string)
        self.assertEqual(r, '{"$or": [{"text": {"$regex": "quick", "$options": "i"}}, {"text": {"$regex": "brown", "$options": "i"}}]}')

        # default field (ie. "text") contains exact phrase
        string = r'''"quick brown"'''
        r = self.parser.parse(string)
        self.assertEqual(r, '{"text": {"$regex": "quick brown", "$options": "i"}}')

    def test_field_names(self):

        # field contains word
        string = r'''status:active'''
        r = self.parser.parse(string)
        self.assertEqual(r, '{"status": {"$regex": "active", "$options": "i"}}')

        # field contains either words
        string = r'''title:(quick OR brown)'''
        r = self.parser.parse(string)
        self.assertEqual(r, '{"$or": [{"title": {"$regex": "quick", "$options": "i"}}, {"title": {"$regex": "brown", "$options": "i"}}]}')

        # field contains either words (default operator)
        string = r'''title:(quick brown)'''
        r = self.parser.parse(string)
        self.assertEqual(r, '{"$or": [{"title": {"$regex": "quick", "$options": "i"}}, {"title": {"$regex": "brown", "$options": "i"}}]}')

        # field contains exact phrase
        string = r'''author:"John Smith"'''
        r = self.parser.parse(string)
        self.assertEqual(r, r'{"author": {"$regex": "\\bJohn Smith\\b", "$options": "i"}}')

        # # any attribute contains word or phrase
        # string = r'''attributes.\*:(quick brown)'''
        # r = self.parser.parse(string)
        # self.assertEqual(r, '??')

        # attribute field has non-null value
        string = r'''_exists_:title'''
        r = self.parser.parse(string)
        self.assertEqual(r, '{"attributes.title": {"$exists": true}}')

        # attribute contains word
        string = r'''foo.vendor:cisco'''
        r = self.parser.parse(string)
        self.assertEqual(r, '{"foo.vendor": {"$regex": "cisco", "$options": "i"}}')

        # attribute contains word ("_" shortcut)
        string = r'''_.vendor:cisco'''
        r = self.parser.parse(string)
        self.assertEqual(r, '{"attributes.vendor": {"$regex": "cisco", "$options": "i"}}')

        # attribute contains either words
        string = r'''attributes.vendor:(cisco OR juniper)'''
        r = self.parser.parse(string)
        self.assertEqual(r, '{"$or": [{"attributes.vendor": {"$regex": "cisco", "$options": "i"}}, {"attributes.vendor": {"$regex": "juniper", "$options": "i"}}]}')

        # attribute contains either words (default operator)
        string = r'''attributes.vendor:(cisco juniper)'''
        r = self.parser.parse(string)
        self.assertEqual(r, '{"$or": [{"attributes.vendor": {"$regex": "cisco", "$options": "i"}}, {"attributes.vendor": {"$regex": "juniper", "$options": "i"}}]}')

        # attribute contains either words ("_" shortcut, default operator)
        string = r'''_.vendor:(cisco juniper)'''
        r = self.parser.parse(string)
        self.assertEqual(r, '{"$or": [{"attributes.vendor": {"$regex": "cisco", "$options": "i"}}, {"attributes.vendor": {"$regex": "juniper", "$options": "i"}}]}')

        # attribute contains exact phrase
        string = r'''foo.vendor:"quick brown"'''
        r = self.parser.parse(string)
        self.assertEqual(r, r'{"foo.vendor": {"$regex": "\\bquick brown\\b", "$options": "i"}}')

        # attribute contains exact phrase ("_" shortcut)
        string = r'''_.vendor:"quick brown"'''
        r = self.parser.parse(string)
        self.assertEqual(r, r'{"attributes.vendor": {"$regex": "\\bquick brown\\b", "$options": "i"}}')

    def test_wildcards(self):

        # ? = single character, * = one or more characters
        string = r'''text:qu?ck bro*'''
        r = self.parser.parse(string)
        self.assertEqual(
            r, '{"$or": [{"text": {"$regex": "\\\\bqu.?ck\\\\b", "$options": "i"}}, {"text": {"$regex": "\\\\bbro.*\\\\b", "$options": "i"}}]}')

    def test_regular_expressions(self):

        string = r'''name:/joh?n(ath[oa]n)/'''
        r = self.parser.parse(string)
        self.assertEqual(r, '{"name": {"$regex": "joh?n(ath[oa]n)", "$options": "i"}}')

    def test_fuzziness(self):
        pass

    def test_proximity_searches(self):
        pass

    def test_ranges(self):

        string = r'''date:[2012-01-01 TO 2012-12-31]'''
        r = self.parser.parse(string)
        self.assertEqual(
            r, '{"$and": [{"date": {"$gte": "2012-01-01"}}, {"date": {"$lte": "2012-12-31"}}]}')

        string = r'''count:[1 TO 5]'''
        r = self.parser.parse(string)
        self.assertEqual(r, '{"$and": [{"count": {"$gte": "1"}}, {"count": {"$lte": "5"}}]}')

        string = r'''tag:{alpha TO omega}'''
        r = self.parser.parse(string)
        self.assertEqual(r, '{"$and": [{"tag": {"$gt": "alpha"}}, {"tag": {"$lt": "omega"}}]}')

        string = r'''count:[10 TO *]'''
        r = self.parser.parse(string)
        self.assertEqual(r, '{"$and": [{"count": {"$gte": "10"}}, {}]}')

        string = r'''date:{* TO 2012-01-01}'''
        r = self.parser.parse(string)
        self.assertEqual(r, '{"$and": [{}, {"date": {"$lt": "2012-01-01"}}]}')

        string = r'''count:[1 TO 5}'''
        r = self.parser.parse(string)
        self.assertEqual(r, '{"$and": [{"count": {"$gte": "1"}}, {"count": {"$lt": "5"}}]}')

    def test_unbounded_ranges(self):

        string = r'''age:>10'''
        r = self.parser.parse(string)
        self.assertEqual(r, '{"age": {"$gt": "10"}}')

        string = r'''age:>=10'''
        r = self.parser.parse(string)
        self.assertEqual(r, '{"age": {"$gte": "10"}}')

        string = r'''age:<10'''
        r = self.parser.parse(string)
        self.assertEqual(r, '{"age": {"$lt": "10"}}')

        string = r'''age:<=10'''
        r = self.parser.parse(string)
        self.assertEqual(r, '{"age": {"$lte": "10"}}')

    def test_boosting(self):
        pass

    def test_boolean_operators(self):

        # OR (||)
        string = r'''"jakarta apache" jakarta'''
        r = self.parser.parse(string)
        self.assertEqual(r, '{"$or": [{"text": {"$regex": "jakarta apache", "$options": "i"}}, {"text": {"$regex": "jakarta", "$options": "i"}}]}')

        string = r'''"jakarta apache" OR jakarta'''
        r = self.parser.parse(string)
        self.assertEqual(r, '{"$or": [{"text": {"$regex": "jakarta apache", "$options": "i"}}, {"text": {"$regex": "jakarta", "$options": "i"}}]}')

        string = r'''"jakarta apache" || jakarta'''
        r = self.parser.parse(string)
        self.assertEqual(r, '{"$or": [{"text": {"$regex": "jakarta apache", "$options": "i"}}, {"text": {"$regex": "jakarta", "$options": "i"}}]}')

        # AND (&&)
        string = r'''"jakarta apache" AND "Apache Lucene"'''
        r = self.parser.parse(string)
        self.assertEqual(r, '{"$and": [{"text": {"$regex": "jakarta apache", "$options": "i"}}, {"text": {"$regex": "Apache Lucene", "$options": "i"}}]}')

        string = r'''"jakarta apache" && "Apache Lucene"'''
        r = self.parser.parse(string)
        self.assertEqual(r, '{"$and": [{"text": {"$regex": "jakarta apache", "$options": "i"}}, {"text": {"$regex": "Apache Lucene", "$options": "i"}}]}')

        # + (required)
        pass

        # NOT (!)
        string = r'''"jakarta apache" NOT "Apache Lucene"'''
        r = self.parser.parse(string)
        self.assertEqual(r, '{"$and": [{"text": {"$regex": "jakarta apache", "$options": "i"}}, {"text": {"$not": {"$regex": "Apache Lucene", "$options": "i"}}}]}')

        string = r'''"jakarta apache" !"Apache Lucene"'''
        r = self.parser.parse(string)
        self.assertEqual(r, '{"$and": [{"text": {"$regex": "jakarta apache", "$options": "i"}}, {"text": {"$not": {"$regex": "Apache Lucene", "$options": "i"}}}]}')

        string = r'''NOT "jakarta apache"'''
        r = self.parser.parse(string)
        self.assertEqual(r, '{"text": {"$not": {"$regex": "jakarta apache", "$options": "i"}}}')

        string = r'''group:"jakarta apache" NOT group:"Apache Lucene"'''
        r = self.parser.parse(string)
        self.assertEqual(r, r'{"$and": [{"group": {"$regex": "\\bjakarta apache\\b", "$options": "i"}}, {"group": {"$not": {"$regex": "\\bApache Lucene\\b", "$options": "i"}}}]}')

        # - (prohibit)
        pass

    def test_grouping(self):

        # field exact match
        string = r'''(quick OR brown) AND fox'''
        r = self.parser.parse(string)
        self.assertEqual(
            r, '{"$and": [{"$or": [{"text": {"$regex": "quick", "$options": "i"}}, {"text": {"$regex": "brown", "$options": "i"}}]}, {"text": {"$regex": "fox", "$options": "i"}}]}')

        # field exact match
        string = r'''status:(active OR pending) title:(full text search)'''
        r = self.parser.parse(string)
        self.assertEqual(
            r, '{"$or": [{"$or": [{"status": {"$regex": "active", "$options": "i"}}, {"status": {"$regex": "pending", "$options": "i"}}]}, {"$or": [{"title": {"$regex": "full", "$options": "i"}}, {"title": {"$regex": "text", "$options": "i"}}]}]}')

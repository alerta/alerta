
import unittest

from werkzeug.datastructures import MultiDict

from alerta.app import create_app, qb

# service, tags (=, !=, =~, !=~)
# attributes (=, !=, =~, !=~)
# everything else (=, !=, =~, !=~)


class SearchTestCase(unittest.TestCase):

    def setUp(self):
        self.app = create_app()

    def test_equal_to(self):

        search_params = MultiDict([('status', 'open'), ('environment', 'Production')])

        with self.app.test_request_context():
            query = qb.from_params(search_params)  # noqa # FIXME

        # self.assertEqual(query.where, 'foo')
        # self.assertEqual(query.sort, 'foo')
        # self.assertEqual(query.group, 'foo')

    def test_attributes(self):

        search_params = MultiDict([('attributes.country_code', 'US')])
        with self.app.test_request_context():
            query = qb.from_params(search_params)

        if self.app.config['DATABASE_URL'].startswith('postgres'):
            self.assertIn('AND attributes @> %(attr_country_code)s', query.where)
            self.assertEqual(query.vars, {'attr_country_code': {'country_code': 'US'}})
        else:
            self.assertEqual(query.where, {'attributes.country_code': 'US'})

    # def test_from_dict(self):
    #
    #     self.qb.from_dict()

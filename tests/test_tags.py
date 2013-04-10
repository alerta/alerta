
import os
import sys
import datetime
import unittest

# If ../alerta/__init__.py exists, add ../ to Python search path, so that
# it will override what happens to be installed in /usr/(local/)lib/python...
possible_topdir = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]),
                                                os.pardir,
                                                os.pardir))
if os.path.exists(os.path.join(possible_topdir, 'alerta', '__init__.py')):
    sys.path.insert(0, possible_topdir)

from alerta.server.database import Mongo
from alerta.common.alert import Alert
from alerta.common import config

CONF = config.CONF


class TestTags(unittest.TestCase):
    """
    Ensures Alert tagging is working as expected.
    """

    def setUp(self):

        config.parse_args(sys.argv)

        self.RESOURCE = 'taghost456'
        self.EVENT = 'TagEvent'
        self.TAGS = ['location:london', 'vendor:ibm']

        self.db = Mongo()

    def test_save_and_tag_alert(self):
        """
        Save an alert to database and tag it.
        """
        alert = Alert(self.RESOURCE, self.EVENT, receive_time=datetime.datetime.utcnow())
        ret = self.db.save_alert(alert)
        self.assertIsInstance(ret, basestring)

        self.db.tag_alert(alert.alertid, self.TAGS)

        self.assertItemsEqual(self.db.get_alert(alert.alertid).tags, [self.TAGS])


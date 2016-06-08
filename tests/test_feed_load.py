# related third party imports
import datetime

from hashlib import sha1

import unittest
from mock import MagicMock, patch

import webapp2
from google.appengine.api import taskqueue
from google.appengine.ext import testbed

# local application/library specific imports
from app.lib.data_connectors import feed_config_connector, core_objects
from app.lib.services.feed_ingestor import FeedIngestor
from app.lib.services.feed_item_parsers import FeedItem
from app.lib.data_connectors.core_objects import PropertyListing, feed_item_metadata

class SampleTestCase(unittest.TestCase):
    def setup(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
    def sample_test(self):
        pass

if __name__ == '__main__':
    unittest.main()

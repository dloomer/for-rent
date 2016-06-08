# testing-specific
from mock import MagicMock, patch
import unittest
from google.appengine.ext import testbed

# related third party imports
import datetime
from hashlib import sha1
import webapp2
from google.appengine.api import taskqueue

# local application/library specific imports
from app.lib.data_connectors import feed_config_connector
from app.lib.services.feed_item_parsers import FeedItem
from app.lib.data_connectors.core_objects import PropertyListing, feed_item_from_url
import app.lib.services.mail as mail

# -*- coding: utf-8 -*-

"""
    Routes are setup in routes.py and added in main.py
"""

# related third party imports
import webapp2

# local application/library specific imports
from app.lib.data_connectors import feed_config_connector
from app.lib.services.feed_item_parsers import CraigslistFeedItem
from app.lib.data_connectors.core_objects import PropertyListing

class DataFeedEntriesHandler(webapp2.RequestHandler):
    def get(self):
        feed_name = self.request.get("feed_name")
        item_urls = self.request.get("urls").split(',')

        feeds_map = feed_config_connector.get_feeds_map()
        feed = feeds_map[feed_name]

        for item_url in item_urls:
            feed_item = CraigslistFeedItem(item_url, feed)
            property_listing = PropertyListing.from_parsed_feed_item(feed_item)
            if not property_listing:
                continue
            if property_listing.is_new:
                # fork into inbox items
                pass
            elif property_listing.is_dirty:
                # update existing inbox items
                pass
                # 

'''
from app.lib.data_connectors import feed_config_connector
from app.lib.services.feed_item_parsers import CraigslistFeedItem
from app.lib.data_connectors.core_objects import PropertyListing

feed_name = 'downtown-seattle'
item_urls = ['http://seattle.craigslist.org/see/apa/5584557553.html']

feeds_map = feed_config_connector.get_feeds_map()
feed = feeds_map[feed_name]

for item_url in item_urls:
    feed_item = CraigslistFeedItem(item_url, feed)
    property_listing = PropertyListing.from_parsed_feed_item(feed_item)
    if property_listing.is_new:
        # fork into inbox items
        pass
    elif property_listing.is_dirty:
        # update existing inbox items
        pass
        # 
'''
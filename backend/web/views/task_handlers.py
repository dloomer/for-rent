# -*- coding: utf-8 -*-

"""
    Routes are setup in routes.py and added in main.py
"""

# related third party imports
import webapp2

# local application/library specific imports
from app.lib.data_connectors import feed_config_connector
from app.lib.services.feed_item_parsers import CraigslistFeedItem, KnockFeedItem, ZillowFeedItem
from app.lib.data_connectors.core_objects import PropertyListing, feed_item_metadata
import app.lib.services.mail as mail

class DataFeedEntriesHandler(webapp2.RequestHandler):
    def get(self):
        feed_name = self.request.get("feed_name")
        item_urls = self.request.get("urls").split(',')

        feeds_map = feed_config_connector.get_feeds_map()
        feed = feeds_map[feed_name]

        if feed['source_type'] == 'craigslist':
            feed_item_cls = CraigslistFeedItem
        elif feed['source_type'] == 'knock':
            feed_item_cls = KnockFeedItem
        elif feed['source_type'] == 'zillow':
            feed_item_cls = ZillowFeedItem
        for item_url in item_urls:
            if feed['source_type'] in ['zillow']:
                cached_metadata = feed_item_metadata(feed_name, item_url)
            else:
                cached_metadata = None
            feed_item = feed_item_cls(item_url, feed, cached_metadata=cached_metadata)
            feed_item.parse()
            property_listing = PropertyListing.from_parsed_feed_item(feed_item)
            if not property_listing:
                continue
            if property_listing.is_new:
                mail.send_property_notification(property_listing.db_object, feed_item.user_url)
            elif property_listing.is_dirty:
                # update existing inbox items
                pass

'''
import app.lib.services.mail as mail
import app.models.core as core_models

item_url = "http://www.google.com"
property_listing = core_models.PropertyListing.get_by_key_name('47.6057333|-122.3161506')
item_url = [item.item_link for item in property_listing.feeditemcache_set()][0]
mail.send_property_notification(property_listing, item_url)
'''
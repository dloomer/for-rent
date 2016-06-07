# -*- coding: utf-8 -*-

"""
    Routes are setup in routes.py and added in main.py
"""

# related third party imports
import json
import webapp2
import logging

# local application/library specific imports
from app.lib.data_connectors import feed_config_connector
from app.lib.services.feed_item_parsers import FeedItem
from app.lib.data_connectors.core_objects import PropertyListing, feed_item_from_url
import app.lib.services.mail as mail

class DataFeedEntriesHandler(webapp2.RequestHandler):
    def get(self):
        feed_name = self.request.get("feed_name")
        item_urls = self.request.get("urls").split(',')

        feeds_map = feed_config_connector.get_feeds_map()
        feed = feeds_map[feed_name]

        _source_types = feed_config_connector.get_source_types()
        use_feed_metadata = _source_types[feed['source_type']].get('use_feed_metadata')

        for item_url in item_urls:
            db_feed_item = feed_item_from_url(feed_name, item_url)
            cached_metadata = db_feed_item.cached_metadata

            db_property_listing = db_feed_item.property_listing \
                if db_feed_item.property_listing else None
            cached_location_data = {
                'geo': [db_property_listing.geo.lat, db_property_listing.geo.lon],
                'address': db_property_listing.address,
                'city': db_property_listing.city,
                'postal_code': db_property_listing.postal_code,
                'neighborhood': db_property_listing.neighborhood,
                'state_code': db_property_listing.state_code,
                'country_code': db_property_listing.country_code
            } if db_property_listing else None
            fetched_data = cached_metadata if use_feed_metadata else None
            feed_item = FeedItem.from_feed(
                feed,
                item_url,
                fetched_data=fetched_data,
                cached_metadata=cached_metadata,
                cached_location_data=cached_location_data
            )
            feed_item.parse()
            try:
                property_listing = PropertyListing.from_parsed_feed_item(feed_item)
            except:
                logging.info("item_url=%s", item_url)
                raise
            if not property_listing or not property_listing.db_object:
                continue
            if property_listing.is_new or property_listing.is_reactivated:
                try:
                    mail.send_property_notification(property_listing.db_object, feed_item.user_url)
                except:
                    logging.info("item_url=%s", item_url)
                    raise
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
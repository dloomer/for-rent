# -*- coding: utf-8 -*-

"""
    Routes are setup in routes.py and added in main.py
"""

# related third party imports
import webapp2
from google.appengine.api import taskqueue

# local application/library specific imports
from app.lib.data_connectors import feed_config_connector, core_objects
from app.lib.services.feed_ingestor import FeedIngestor
from app.lib.services.feed_item_parsers import FeedItem
from app.lib.data_connectors.core_objects import PropertyListing, feed_item_metadata

class LoadFeedDataRequestHandler(webapp2.RequestHandler):
    def get(self):
        feed_config = feed_config_connector.get_feed_config()
        feeds = feed_config['feeds']

        for feed in feeds:
            feed_ingestor = FeedIngestor(feed)
            urls_for_update = feed_ingestor.urls_for_update()
            if len(urls_for_update):
                task = taskqueue.Task(
                    url='/task/process_data_feed_entries',
                    params={
                        'feed_name': feed['name'],
                        'urls': ','.join(urls_for_update)
                    },
                    method='GET'
                )
                task.add()

class RefetchListingStatusRequestHandler(webapp2.RequestHandler):
    def get(self):

        feeds_map = feed_config_connector.get_feeds_map()

        active_properties = core_objects.get_active_property_listings()
        for property_listing in active_properties:
            parsed_feed_items = []
            for feed_item in core_objects.get_listing_source_items(property_listing):
                feed = feeds_map[feed_item.feed_name]
                item_url = feed_item.item_link
                if feed['source_type'] in ['zillow']:
                    cached_metadata = feed_item_metadata(feed_item.feed_name, item_url)
                else:
                    cached_metadata = None
                cached_location_data = {
                    'geo': [property_listing.geo.lat, property_listing.geo.lon],
                    'address': property_listing.address,
                    'city': property_listing.city,
                    'postal_code': property_listing.postal_code,
                    'neighborhood': property_listing.neighborhood,
                    'state_code': property_listing.state_code,
                    'country_code': property_listing.country_code
                }
                feed_item = FeedItem.from_feed(
                    feed,
                    item_url,
                    cached_metadata=cached_metadata,
                    cached_location_data=cached_location_data
                )
                feed_item.parse()
                parsed_feed_items.append(feed_item)
            property_listing = PropertyListing.from_parsed_feed_items(
                parsed_feed_items,
                db_object=property_listing
            )

class EnqueueTaskRequestHandler(webapp2.RequestHandler):
    def get(self):
        task = taskqueue.Task(
            url=self.request.get("url"),
            method='GET'
        )
        task.add()

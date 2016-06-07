# -*- coding: utf-8 -*-

"""
    Routes are setup in routes.py and added in main.py
"""

# related third party imports
import datetime
import logging
from hashlib import sha1
import webapp2
from google.appengine.api import taskqueue

# local application/library specific imports
from app.lib.data_connectors import feed_config_connector, core_objects
from app.lib.services.feed_ingestor import FeedIngestor
from app.lib.services.feed_item_parsers import FeedItem
from app.lib.data_connectors.core_objects import PropertyListing, feed_item_metadata

class LoadFeedDataRequestHandler(webapp2.RequestHandler):
    def get(self):
        feed_name = self.request.get('feed_name')

        feed_config = feed_config_connector.get_feed_config()

        if feed_name:
            feeds_map = feed_config_connector.get_feeds_map()
            feed = feeds_map[feed_name]
            _source_types = feed_config_connector.get_source_types()
            _feed_type = _source_types[feed['source_type']]['feed_type']
            feed_ingestor = FeedIngestor(feed)
            if _feed_type == 'rss':
                urls_for_update = feed_ingestor.urls_for_update()
            else:
                urls_for_update = feed_ingestor.urls()
            if len(urls_for_update):
                batch_size = 5
                batch_count = (len(urls_for_update) + batch_size - 1) / batch_size
                for batch_number in range(batch_count):
                    batch_start = batch_number * batch_size
                    batch_end = (batch_number + 1) * batch_size

                    task_url = "/task/process_data_feed_entries"
                    urls_parm = ','.join(urls_for_update[batch_start:batch_end])

                    unique_id_str = self.request.environ['PATH_INFO'] + \
                        '?' + self.request.environ['QUERY_STRING'] + \
                        '|' + task_url + \
                        '|' + urls_parm + \
                        '|' + feed['name']

                    try:
                        task = taskqueue.Task(
                            url=task_url,
                            params={
                                'feed_name': feed['name'],
                                'urls': urls_parm
                            },
                            name=sha1(unique_id_str).hexdigest(),
                            method='GET'
                        )
                        task.add()
                    except taskqueue.TaskAlreadyExistsError:
                        pass
                    except taskqueue.TombstonedTaskError:
                        pass
        else:
            feeds = feed_config['feeds']
            for feed in feeds:
                task_url = "/batch/load_feed_data"

                unique_id_str = self.request.environ['PATH_INFO'] + \
                    '?' + self.request.environ['QUERY_STRING'] + \
                    '|' + task_url + \
                    '|' + feed['name']
                try:
                    task = taskqueue.Task(
                        url=task_url,
                        params={
                            'feed_name': feed['name'],
                            'queued_time': datetime.datetime.now()
                        },
                        name=sha1(unique_id_str).hexdigest(),
                        method='GET'
                    )
                    task.add()
                except taskqueue.TaskAlreadyExistsError:
                    pass
                except taskqueue.TombstonedTaskError:
                    pass

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
            params={
                'queued_time': datetime.datetime.now(),
            },
            method='GET'
        )
        task.add()

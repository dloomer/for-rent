# -*- coding: utf-8 -*-

"""
    Routes are setup in routes.py and added in main.py
"""

# related third party imports
import webapp2
from google.appengine.api import taskqueue

# local application/library specific imports
from app.lib.data_connectors import feed_config_connector
from app.lib.services.feed_ingestor import FeedIngestor

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

class EnqueueLoadFeedDataRequestHandler(webapp2.RequestHandler):
    def get(self):
        task = taskqueue.Task(
            url='/batch/load_feed_data',
            method='GET'
        )
        task.add()

# -*- coding: utf-8 -*-

# standard library imports
from google.appengine.api import memcache
from google.appengine.ext import db

# local application/library specific imports
import app.models.core as core_models


class FeedCache(object):
    def __init__(self, feed_name):
        self.feed_name = feed_name
        self.cache_key = "feed-items-" + self.feed_name

    def cached_links(self, reset=False):
        if not reset:
            # pylint: disable=no-member
            cached = memcache.get(self.cache_key)
            # pylint: enable=no-member
        else:
            cached = None
        if cached:
            links = cached
        else:
            db_cached = core_models.FeedItemCache \
                .all() \
                .filter(
                    "feed_name = ", self.feed_name
                ).fetch(1000)
            links = [cache.item_link for cache in db_cached]

        # pylint: disable=no-member
        memcache.set(self.cache_key, links)
        # pylint: enable=no-member

        return links

    def add_item_link(self, item_link, cached_metadata=None):
        db_cached = core_models.FeedItemCache \
            .get_or_insert_by_values(
                feed_name=self.feed_name,
                item_link=item_link,
                cached_metadata=cached_metadata,
            )
        db_cached.put()

        cached_links = self.cached_links()
        cached_links.append(item_link)

        # pylint: disable=no-member
        memcache.set(self.cache_key, cached_links)
        # pylint: enable=no-member

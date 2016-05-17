# -*- coding: utf-8 -*-

# standard library imports
from StringIO import StringIO
from urlparse import urlparse

# related third party imports
from google.appengine.api import urlfetch

try:
    import feedparser
except ImportError:
    from third_party import feedparser

# local application/library specific imports
from app.lib.data_connectors.feed_cache import FeedCache

class FeedIngestor(object):
    def __init__(self, feed):
        self.feed_name = feed['name']
        self.feed_url = feed['url']
        self.hostname_proxy = feed.get('hostname_proxy')
        self._cached_links = []
        self._results = []
        self._is_fetched = False

    def _url_for_urlfetch(self, url):
        if self.hostname_proxy:
            parsed = urlparse(url)
            proxied_url = parsed.scheme + '://' + self.hostname_proxy + parsed.path + \
                ('?' + parsed.query if parsed.query else '')
            return proxied_url
        else:
            return url

    def _fetch(self):
        response = urlfetch.fetch(self._url_for_urlfetch(self.feed_url))
        parsed_feed = feedparser.parse(StringIO(response.content))

        cache = FeedCache(self.feed_name)

        self._cached_links = cache.cached_links()
        self._results = parsed_feed.entries

        results_not_cached = [
            result for result in self._results
            if result.links[0]['href'] not in self._cached_links
        ]
        for result in results_not_cached:
            cache.add_item_link(result.links[0]['href'])

        self._is_fetched = True

    def entries_for_update(self):
        if not self._is_fetched:
            self._fetch()
        return [
            entry for entry in self._results
            if entry.links[0]['href'] not in self._cached_links
        ]

    def urls_for_update(self):
        return [
            entry.links[0]['href']
            for entry in self.entries_for_update()
        ]

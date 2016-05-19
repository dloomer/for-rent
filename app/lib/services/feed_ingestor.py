# -*- coding: utf-8 -*-

# standard library imports
import json
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

FEED_TYPE_MAP = {
    'craigslist': "rss",
    'knock': "json"
}
class FeedIngestor(object):
    def __init__(self, feed):
        self.feed_name = feed['name']
        self.source_type = feed['source_type']
        self.feed_type = FEED_TYPE_MAP[self.source_type]
        self.feed_url = feed['url']
        self.feed_post_body = feed.get('post_body')
        self.hostname_proxy = feed.get('hostname_proxy')
        self.item_url_path = feed.get('item_url_path')
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

    def _item_link(self, item):
        if self.feed_type == "rss":
            return item.links[0]['href']
        elif self.feed_type == "json":
            return item['url']

    def _fetch(self):
        if self.feed_type == "rss":
            response = urlfetch.fetch(self._url_for_urlfetch(self.feed_url))
            parsed_feed = feedparser.parse(StringIO(response.content))
            self._results = parsed_feed.entries
        elif self.feed_type == "json":
            if self.feed_post_body:
                response = urlfetch.fetch(
                    url=self._url_for_urlfetch(self.feed_url),
                    payload=json.dumps(self.feed_post_body),
                    method=urlfetch.POST
                )
            else:
                response = urlfetch.fetch(self._url_for_urlfetch(self.feed_url))
            parsed_feed = json.loads(StringIO(response.content))
            self._results = []
            for _, _address_results in parsed_feed['data']['results'].items():
                self._results.extend(_address_results)
            for _result in self._results:
                _result['url'] = self.item_url_path + _result['id']

        cache = FeedCache(self.feed_name)

        self._cached_links = cache.cached_links()

        results_not_cached = [
            result for result in self._results
            if self._item_link(result) not in self._cached_links
        ]
        for result in results_not_cached:
            cache.add_item_link(self._item_link(result))

        self._is_fetched = True

    def entries_for_update(self):
        if not self._is_fetched:
            self._fetch()
        return [
            entry for entry in self._results
            if self._item_link(entry) not in self._cached_links
        ]

    def urls_for_update(self):
        return [
            self._item_link(entry)
            for entry in self.entries_for_update()
        ]

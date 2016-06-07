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
from app.lib.data_connectors import feed_config_connector

class FeedIngestor(object):
    def __init__(self, feed):
        self.feed_name = feed['name']
        self.source_type = feed['source_type']
        _source_types = feed_config_connector.get_source_types()
        self.feed_type = _source_types[self.source_type]['feed_type']
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
        cached_metadata = None
        if self.feed_type == "rss":
            for _ in range(3):
                try:
                    response = urlfetch.fetch(self._url_for_urlfetch(self.feed_url), deadline=20)
                    break
                except ConnectionClosedError:
                    pass
                except DeadlineExceededError:
                    pass
            parsed_feed = feedparser.parse(StringIO(response.content))
            self._results = parsed_feed.entries
        elif self.feed_type == "json":
            for _ in range(3):
                try:
                    if self.feed_post_body:
                        response = urlfetch.fetch(
                            url=self._url_for_urlfetch(self.feed_url),
                            payload=json.dumps(self.feed_post_body),
                            method=urlfetch.POST,
                            deadline=20
                        )
                    else:
                        response = urlfetch.fetch(self._url_for_urlfetch(self.feed_url), deadline=20)
                    break
                except ConnectionClosedError:
                    pass
                except DeadlineExceededError:
                    pass
            parsed_feed = json.loads(response.content)
            self._results = []
            if self.source_type == 'knock':
                for _, _coordinate_content in parsed_feed['data'].items():
                    for _, _address_results in _coordinate_content['results'].items():
                        self._results.extend(_address_results)
                for _result in self._results:
                    _result['url'] = self.item_url_path + _result['id']
            elif self.source_type == 'zillow':
                all_listings = parsed_feed['map']['properties'] + parsed_feed['map']['buildings']
                for listing in all_listings:
                    _result = {}
                    if len(listing) == 8:
                        # property
                        _result['geo'] = [float(listing[1])/(10.0**6), float(listing[2])/(10.0**6)]
                        details = listing[7]
                        _result['price'] = details[0]
                        _result['bedrooms'] = details[1]
                        _result['bathrooms'] = int(details[2])
                        _result['square_feet'] = details[3]
                        _result['image_url'] = details[5]
                        _result['url'] = self.item_url_path + \
                            "/jsonp/Hdp.htm?zpid=%s&lhdp=true&callback=x" % listing[0]
                    elif len(listing) == 5:
                        # building
                        _result['geo'] = [float(listing[0])/(10.0**6), float(listing[1])/(10.0**6)]
                        details = listing[4]
                        _result['price'] = details[0]
                        _result['bedrooms'] = details[3]
                        _result['bathrooms'] = int(details[4])
                        _result['square_feet'] = details[5]
                        _result['image_url'] = details[1]
                        _result['url'] = self.item_url_path + \
                            "/jsonp/Bdp.htm?lat=%s&lon=%s&pageNum=1&lhdp=true&callback=x" % (
                                _result['geo'][0],
                                _result['geo'][1]
                            )
                    self._results.append(_result)

        cache = FeedCache(self.feed_name)

        self._cached_links = cache.cached_links()

        if self.feed_type == "rss":
            results_not_cached = [
                result for result in self._results
                if self._item_link(result) not in self._cached_links
            ]
            for result in results_not_cached:
                cache.add_item_link(self._item_link(result))
        else:
            for result in self._results:
                cache.add_item_link(self._item_link(result), cached_metadata=result)

        self._is_fetched = True

    def entries(self):
        if not self._is_fetched:
            self._fetch()
        return self._results

    def urls(self):
        return [
            self._item_link(entry)
            for entry in self.entries()
        ]

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

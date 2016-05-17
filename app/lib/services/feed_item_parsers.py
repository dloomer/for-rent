# -*- coding: utf-8 -*-

# standard library imports
import json
from StringIO import StringIO
from urlparse import urlparse
from math import sin, cos, sqrt, atan2, radians

# related third party imports
from google.appengine.api import urlfetch

try:
    from bs4 import BeautifulSoup
except ImportError:
    from third_party.bs4 import BeautifulSoup

# local application/library specific imports
from app.lib.utils import string_utils

def _distance(point_a, point_b):
    radius = 6372.795

    lat1, lng1 = radians(point_a[0]), radians(point_a[1])
    lat2, lng2 = radians(point_b[0]), radians(point_b[1])

    sin_lat1, cos_lat1 = sin(lat1), cos(lat1)
    sin_lat2, cos_lat2 = sin(lat2), cos(lat2)

    delta_lng = lng2 - lng1
    cos_delta_lng, sin_delta_lng = cos(delta_lng), sin(delta_lng)

    dist = \
        atan2(sqrt((cos_lat2 * sin_delta_lng) ** 2 +
                   (cos_lat1 * sin_lat2 -
                    sin_lat1 * cos_lat2 * cos_delta_lng) ** 2),
              sin_lat1 * sin_lat2 + cos_lat1 * cos_lat2 * cos_delta_lng)

    return radius * dist

# TODO - text body property, for keyword matching
# TODO - how to automatically convey breed restrictions without false positives for
# "no breed restrictions" etc
class FeedItem(object):
    def __init__(self, url, feed, fetched_contents=None):
        self.page_url = url
        self.price = ""
        self.title = ""
        self.address = ""
        self.city = ""
        self.state_code = ""
        self.country_code = ""
        self.neighborhood = ""
        self.postal_code = ""
        self.geo = []
        self.feed_region = feed['region']
        self.hostname_proxy = feed.get('hostname_proxy')
        self.feed_name = feed['name']
        self.keywords = []
        self.image_url = ""
        self.posting_body = ""
        self._is_fetched = False
        self._response = None
        self._target_geo = []
        self._target_geo_accuracy = -1
        if fetched_contents:
            self._response_text = fetched_contents
            self._is_fetched = True
        self.is_active = True

    def _url_for_urlfetch(self, url):
        if self.hostname_proxy:
            parsed = urlparse(url)
            return parsed.scheme + '://' + self.hostname_proxy + parsed.path + \
                ('?' + parsed.query if parsed.query else '')
        else:
            return url

    def _fetch(self):
        self._response_text = urlfetch.fetch(self._url_for_urlfetch(self.page_url)).content
        self._is_fetched = True

    def parse(self):
        if not self._is_fetched:
            self._fetch()

    def _parse_address(self, address_text):
        address_text = address_text.split(' at ')[0]
        address_text = address_text.strip()
        if address_text.startswith("("):
            address_text = address_text[1:]
        if address_text.endswith(")"):
            address_text = address_text[:-1]
        address_text = address_text.strip()

        # TODO: move API key into conig file with .gitignore
        url = \
            "https://maps.googleapis.com/maps/api/geocode/json?address=%s,%s" \
            "&key=AIzaSyCudFnRAe8qVt0mXe2fcmVAzs-BjvRzaf8" % (
                string_utils.unicode_urlencode(address_text),
                string_utils.unicode_urlencode(self.feed_region)
            )
        response_dict = json.loads(urlfetch.fetch(url).content)
        if response_dict['results']:
            top_result = response_dict['results'][0]
            if top_result['geometry']['location_type'] == "ROOFTOP":
                street_number = ""
                street = ""
                city = ""
                postal_code = ""
                neighborhood = ""
                state_code = ""
                country_code = ""
                for comp in top_result['address_components']:
                    if "street_number" in comp['types']:
                        street_number = comp['short_name']
                    elif "route" in comp['types']:
                        street = comp['short_name']
                    elif "country" in comp['types']:
                        country_code = comp['short_name']
                    elif "locality" in comp['types']:
                        city = comp['short_name']
                    elif "postal_code" in comp['types']:
                        postal_code = comp['short_name']
                    elif "administrative_area_level_1" in comp['types']:
                        state_code = comp['short_name']
                    elif "neighborhood" in comp['types']:
                        neighborhood = comp['long_name']
                address = street_number + ' ' + street
                location = top_result['geometry']['location']
                geo = [location['lat'], location['lng']]
                distance = _distance(geo, self._target_geo) \
                    if self._target_geo else 0
                if distance < 0.08 or \
                   (distance < 5.0 and \
                    address_text.lower().startswith(address.lower()) or \
                    address.lower().startswith(address_text.lower())):
                    self.geo = geo
                    self.address = address
                    self.city = city
                    self.postal_code = postal_code
                    self.neighborhood = neighborhood
                    self.state_code = state_code
                    self.country_code = country_code
        else:
            raise Exception(response_dict['error_message'])

class CraigslistFeedItem(FeedItem):
    def __init__(self, url, feed):
        super(CraigslistFeedItem, self).__init__(url, feed)

    def parse(self):
        super(CraigslistFeedItem, self).parse()

        soup = BeautifulSoup(StringIO(self._response_text), "html.parser")
        title_text_node = soup.find("span", {'class': "postingtitletext"})
        if not title_text_node:
            self.is_active = False
            return
        self.price = title_text_node.find("span", {'class': "price"}).text
        self.title = title_text_node.find("span", {'id': "titletextonly"}).text
        map_node = soup.find("div", {'id': "map"})
        self._target_geo = [
            float(map_node['data-latitude']),
            float(map_node['data-longitude'])
        ] if map_node else []
        self._target_geo_accuracy = int(map_node['data-accuracy']) \
            if map_node else -1

        map_attrs_node = soup.find("div", {'class': "mapAndAttrs"})
        map_address_node = map_attrs_node.find("div", {'class': "mapaddress"}) \
            if map_attrs_node else None
        map_address_str = map_address_node.text \
            if map_address_node else ""
        if map_address_str:
            self._parse_address(map_address_str)
        if not self.address:
            small_node = title_text_node.find("small")
            map_address_str = small_node.text if small_node else ""
            if map_address_str:
                self._parse_address(map_address_str)
        attr_group_nodes = soup.findAll("p", {'class': "attrgroup"})
        for attr_group_node in attr_group_nodes:
            self.keywords.extend(
                [
                    span.text
                    for span
                    in attr_group_node.findAll("span")
                ]
            )
        gallery_node = soup.find("div", {'class': "gallery"})
        first_image_node = gallery_node.find("img") \
            if gallery_node else None
        self.image_url = first_image_node['src'] \
            if first_image_node else ""
        self.posting_body = soup.find("section", {'id': "postingbody"}).text

'''
from app.lib.services.feed_item_parsers import CraigslistFeedItem
item = CraigslistFeedItem(
    "http://seattle.craigslist.org/see/apa/5569185899.html",
    {'region': "Seattle, WA, US", 'hostname_proxy': "craigslist.localhost"}
)
item.parse()
'''
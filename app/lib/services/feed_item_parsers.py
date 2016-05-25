# -*- coding: utf-8 -*-

# standard library imports
import json
import logging
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
from app.lib.data_connectors import feed_config_connector

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

def _fact_contains(fact_value, search_for):
    if isinstance(fact_value, list):
        return search_for.lower() in [_.lower() for _ in fact_value]
    elif isinstance(fact_value, str) or isinstance(fact_value, unicode):
        return fact_value.lower().find(search_for.lower()) >= 0
    else:
        return fact_value == search_for

class FeedItem(object):
    def __init__(
            self,
            url,
            feed,
            fetched_contents=None,
            cached_metadata=None,
            cached_location_data=None
        ):
        self.page_url = url
        self.user_url = url
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
        self.feed_source_type = feed['source_type']
        self.feed_post_filter_criteria = feed.get('post_filter_criteria', {})
        self.cached_metadata = cached_metadata
        self.keywords = []
        self.facts = {}
        self.image_url = ""
        self.posting_body = ""
        self.is_rejected = False
        self._is_fetched = False
        self._http_response = None
        self._target_geo = []
        self._target_geo_accuracy = -1
        if fetched_contents:
            self._response_text = fetched_contents
            self._is_fetched = True
        self.is_active = True

    def _url_for_urlfetch(self, url):
        parsed = urlparse(url)

        if self.hostname_proxy:
            return parsed.scheme + '://' + self.hostname_proxy + parsed.path + \
                ('?' + parsed.query if parsed.query else '')
        elif self.feed_source_type == 'knock':
            return 'https://api.knockrentals.com/v1' + parsed.path
        else:
            return url

    def _fetch(self):
        self._http_response = urlfetch.fetch(
            self._url_for_urlfetch(self.page_url),
            deadline=20
        )
        self._response_text = self._http_response.content
        self._is_fetched = True

    def parse(self):
        if not self._is_fetched:
            self._fetch()

    def validate(self):
        self.is_rejected = False
        if not self.is_active:
            # Cannot be both inactive and rejected.
            return
        feed_config = feed_config_connector.get_feed_config()
        filter_criteria = feed_config.get('post_filter_criteria', {})
        _source_types = feed_config_connector.get_source_types(feed_config=feed_config)
        filter_criteria.update(_source_types[self.feed_source_type].get('post_filter_criteria', {}))
        filter_criteria.update(self.feed_post_filter_criteria)
        for validation_group_name, validation_group in \
            filter_criteria.items():
            if validation_group_name == 'facts':
                for fact_name, criteria in validation_group.items():
                    if criteria['operation'] == "must_contain":
                        if not _fact_contains(self.facts.get(fact_name, ""), criteria['value']):
                            logging.info(
                                "Rejecting feed item %s: Fact '%s' does not contain '%s'",
                                self.page_url,
                                fact_name,
                                criteria['value']
                            )
                            logging.debug("self.facts=%s", self.facts)
                            logging.debug(
                                "filter_criteria=%s",
                                filter_criteria
                            )
                            self.is_rejected = True
                            return
                    elif criteria['operation'] == "must_not_contain":
                        if self.facts.get(fact_name, "") and \
                            _fact_contains(self.facts[fact_name], criteria['value']):
                            logging.info(
                                "Rejecting feed item %s: Fact '%s' contains '%s'",
                                self.page_url,
                                fact_name,
                                criteria['value']
                            )
                            logging.debug("self.facts=%s", self.facts)
                            logging.debug(
                                "filter_criteria=%s",
                                filter_criteria
                            )
                            self.is_rejected = True
                            return


    def _parse_address(self, address_text="", known_geo=None):
        address_text = address_text.split(' at ')[0]
        address_text = address_text.strip()
        if address_text.startswith("("):
            address_text = address_text[1:]
        if address_text.endswith(")"):
            address_text = address_text[:-1]
        address_text = address_text.strip()

        # TODO: move API key into conig file with .gitignore
        if address_text:
            lookup = "address=%s,%s"% (
                string_utils.unicode_urlencode(address_text),
                string_utils.unicode_urlencode(self.feed_region)
            )
        elif known_geo:
            lookup = "latlng=%s" % ','.join([str(_) for _ in known_geo])
        else:
            return

        url = \
            "https://maps.googleapis.com/maps/api/geocode/json?%s" \
            "&key=AIzaSyCudFnRAe8qVt0mXe2fcmVAzs-BjvRzaf8" % lookup
        logging.debug("url=%s", url)
        response_dict = json.loads(urlfetch.fetch(url).content)
        if response_dict['results']:
            top_result = response_dict['results'][0]
            logging.debug(
                "top_result['geometry']['location_type']=%s",
                top_result['geometry']['location_type']
            )

            if top_result['geometry'].get('bounds'):
                ne_bounds = top_result['geometry']['bounds']['northeast']
                sw_bounds = top_result['geometry']['bounds']['southwest']
                boundary_distance = _distance(
                    (ne_bounds['lat'], ne_bounds['lng']),
                    (sw_bounds['lat'], sw_bounds['lng'])
                )
                logging.debug("boundary_distance=%s", boundary_distance)
                # 0.00140772080019, RANGE_INTERPOLATED

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
                logging.debug("distance=%s", distance)
                logging.debug("geo=%s", geo)
                logging.debug("self._target_geo=%s", self._target_geo)
                if distance < 0.08 or \
                   (distance < 5.0 and \
                    address_text.lower().startswith(address.lower()) or \
                    address.lower().startswith(address_text.lower())) or \
                   known_geo is not None:
                    self.geo = geo
                    self.address = address
                    self.city = city
                    self.postal_code = postal_code
                    self.neighborhood = neighborhood
                    self.state_code = state_code
                    self.country_code = country_code
        else:
            raise Exception(response_dict['error_message'])

    @staticmethod
    def from_feed(feed, item_url, cached_metadata=None):
        if feed['source_type'] == 'craigslist':
            return CraigslistFeedItem(item_url, feed, cached_metadata=cached_metadata)
        elif feed['source_type'] == 'knock':
            return KnockFeedItem(item_url, feed, cached_metadata=cached_metadata)
        elif feed['source_type'] == 'zillow':
            return ZillowFeedItem(item_url, feed, cached_metadata=cached_metadata)

class CraigslistFeedItem(FeedItem):
    def __init__(
            self,
            url,
            feed,
            fetched_contents=None,
            cached_metadata=None,
            cached_location_data=None
        ):
        super(CraigslistFeedItem, self).__init__(
            url,
            feed,
            fetched_contents=fetched_contents,
            cached_metadata=cached_metadata,
            cached_location_data=cached_location_data
        )

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
            self._parse_address(address_text=map_address_str)
        if not self.address:
            small_node = title_text_node.find("small")
            map_address_str = small_node.text if small_node else ""
            if map_address_str:
                self._parse_address(address_text=map_address_str)
        if not self.address and \
            (self._target_geo_accuracy <= 7 and self._target_geo_accuracy >= 0):
            self._parse_address(known_geo=self._target_geo)

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

class KnockFeedItem(FeedItem):
    def __init__(
            self,
            url,
            feed,
            fetched_contents=None,
            cached_metadata=None,
            cached_location_data=None
        ):
        super(KnockFeedItem, self).__init__(
            url,
            feed,
            fetched_contents=fetched_contents,
            cached_metadata=cached_metadata,
            cached_location_data=cached_location_data
        )

    def parse(self):
        super(KnockFeedItem, self).parse()

        listing_dict = json.loads(self._response_text)['listing']
        self.price = listing_dict['leasing']['monthlyRent']
        bedrooms = int(listing_dict['floorplan']['bedrooms'])
        bathrooms = int(listing_dict['floorplan']['bathrooms'])
        square_feet = int(listing_dict['floorplan']['size'])
        self.title = "%s - %s beds, %s baths, %s sq. ft." % (
            '${:,.2f}'.format(self.price),
            bedrooms,
            bathrooms,
            '{:,}'.format(square_feet)
        )
        coordinates = listing_dict['location']['geo']['coordinates']
        self._target_geo = [
            coordinates[1],
            coordinates[0]
        ]
        self._target_geo_accuracy = 0

        self._parse_address(address_text=listing_dict['location']['address']['street'])
        if not self.address:
            self._parse_address(known_geo=self._target_geo)

        self.keywords = [listing_dict['location']['propertyType']]
        if listing_dict['coverPhoto']:
            self.image_url = listing_dict['coverPhoto']['url']
        elif listing_dict['photos']:
            self.image_url = listing_dict['photos'][0]['url']
        self.posting_body = listing_dict['description']['full']

        url = "https://api.knockrentals.com/v1/listing/rd2eAxAqOQM88Wxg/availableTimes"
        response_dict = json.loads(urlfetch.fetch(url).content)
        self.is_active = \
            len(response_dict.get('acceptable_slots', [])) > 0 or \
            len(response_dict.get('open_house_slots', [])) > 0 or \
            len(response_dict.get('prime_time_slots', [])) > 0 or \
            len(response_dict.get('requestable_slots', [])) > 0

class ZillowFeedItem(FeedItem):
    def __init__(
            self,
            url,
            feed,
            fetched_contents=None,
            cached_metadata=None,
            cached_location_data=None
        ):
        super(ZillowFeedItem, self).__init__(
            url,
            feed,
            fetched_contents=fetched_contents,
            cached_metadata=cached_metadata,
            cached_location_data=cached_location_data
        )

    def parse(self):
        super(ZillowFeedItem, self).parse()

        self.price = self.cached_metadata['price']
        bedrooms = self.cached_metadata['bedrooms']
        bathrooms = self.cached_metadata['bathrooms']
        square_feet = self.cached_metadata['square_feet']
        if self.cached_metadata['image_url']:
            self.image_url = self.cached_metadata['image_url'].replace('/p_a/', '/p_f/')
        self._target_geo = self.cached_metadata['geo']
        self._target_geo_accuracy = 0
        if self.price.endswith("/mo"):
            self.price = self.price[:-3]
        if self.price.endswith("+"):
            self.price = self.price[:-1]
        if self.price.startswith("$"):
            self.price = self.price[1:]
        self.price = self.price.replace(",", "")

        response_text = self._response_text.strip()
        start_js_1 = "x("
        start_js_2 = "if (typeof x!==\"undefined\") { x( "
        body_script = ", \"bodyScript\" : "
        if response_text.startswith(start_js_1):
            response_text = response_text[len(start_js_1):].strip()
        elif response_text.startswith(start_js_2):
            response_text = response_text[len(start_js_2):].strip()
        if response_text.find(body_script) > 0:
            response_text = response_text[:response_text.find(body_script)] + "}"
        if response_text.endswith(");"):
            response_text = response_text[:-2].strip()

        try:
            listing_dict = json.loads(response_text)
        except ValueError:
            if self._http_response.status_code in [404]:
                self.is_active = False
                return
            else:
                logging.debug("self.page_url=%s", self.page_url)
                logging.debug("self.user_url=%s", self.user_url)
                logging.debug("response_text=%s", response_text)
                logging.debug("self._http_response.status_code=%s", self._http_response.status_code)
                logging.debug("self._http_response.headers=%s", self._http_response.headers)
                raise

        if listing_dict.get('redirectLocation') and \
            (not listing_dict.get('actionBar') or not listing_dict.get('bodyContent')):
            self.is_active = False
            return

        soup = BeautifulSoup(StringIO(listing_dict['actionBar']), "html.parser")
        self.user_url = "http://www.zillow.com" + \
            soup.find("li", {'id': "hdp-popout-menu"}).find("a")['href']
        soup = BeautifulSoup(StringIO(listing_dict['bodyContent']), "html.parser")
        addr_city = soup.find("span", {'class': "zsg-h2 addr_city"})
        if addr_city:
            address_text = addr_city.text
        else:
            addr_city = soup.find("h2", {'class': "zsg-h5"})
            if addr_city:
                address_text = addr_city.text
            else:
                address_text = ""

        address_split = address_text.split(', ')
        if len(address_split) > 2:
            address_text = ', '.join(address_split[:-2])
        else:
            address_text = ""
        self.title = "%s - %s beds, %s baths, %s sq. ft." % (
            '${:,.2f}'.format(float(self.price)),
            bedrooms,
            bathrooms,
            '{:,}'.format(square_feet)
        )

        if address_text:
            self._parse_address(address_text=address_text)
        if not self.address:
            self._parse_address(known_geo=self._target_geo)

        self.is_active = False
        avail_node = soup.find("div", {'data-tableid': "available"})
        if avail_node:
            self.is_active = True
        else:
            listing_icon = soup.find("span", {'id': "listing-icon"})
            if listing_icon:
                self.is_active = listing_icon['data-icon-class'] == "zsg-icon-for-rent"

        self.keywords = ['property']
        self.posting_body = listing_dict['bodyContent']

        def _fact_numeric_value(fact_str):
            if fact_str.endswith(" sqft"):
                fact_str = fact_str[:-5]
            fact_str = fact_str.replace(',', '')
            if fact_str.startswith('$'):
                fact_str = fact_str[1:]
            return float(fact_str)

        if soup.find("div", {'class': "building-attrs-group"}):
            fact_group_container_nodes = soup.findAll("div", {'class': "building-attrs-group"})
        elif soup.find("div", {'class': "fact-group-container"}):
            fact_group_container_nodes = soup.findAll("div", {'class': "fact-group-container"})
        else:
            fact_group_container_nodes = []
        for fact_group_container_node in fact_group_container_nodes:
            h3_node = fact_group_container_node.find("h3")
            group_title = h3_node.text if h3_node else ""
            if not group_title:
                h4_node = fact_group_container_node.find("h4")
                group_title = h4_node.text if h4_node else ""
            for list_item_node in fact_group_container_node.findAll("li"):
                node_text = list_item_node.text
                if not node_text.find(":"):
                    continue
                fact_name, _, fact_str = node_text.partition(': ')
                if not fact_name:
                    continue
                if not fact_str:
                    self.keywords.append(fact_name.lower())
                else:
                    fact_key = string_utils.slugify(fact_name).lower()
                    try:
                        self.facts[fact_key] = _fact_numeric_value(fact_str)
                    except ValueError:
                        if fact_str in ["Yes", "No"]:
                            self.facts[fact_key] = fact_str == "Yes"
                        else:
                            self.facts[fact_key] = fact_str.split(', ')

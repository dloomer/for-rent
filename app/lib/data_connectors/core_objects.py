# -*- coding: utf-8 -*-

# standard library imports
from google.appengine.ext import db

# local application/library specific imports
import app.models.core as core_models
from app.lib.data_connectors.image import Image

def _feed_item_from_url(feed_name, url):
    item_key_name = core_models.FeedItemCache.generate_key_name(
        feed_name=feed_name,
        item_link=url
    )
    return core_models.FeedItemCache.get_by_key_name(item_key_name)

def feed_item_metadata(feed_name, url):
    db_feed_item = _feed_item_from_url(feed_name, url)
    # pylint: disable=no-member
    return db_feed_item.cached_metadata if db_feed_item else {}
    # pylint: enable=no-member

class PropertyListing(object):
    def __init__(self, image_url=None, **kwargs):
        if isinstance(kwargs['geo'], list):
            kwargs['geo'] = db.GeoPt(*kwargs['geo'])
        self.db_object, self.is_new = core_models.PropertyListing \
            .get_or_insert_with_flag(**kwargs)
        self.is_dirty = False
        if not self.is_new:
            # special logic for pricing
            if kwargs['start_price'] < self.db_object.start_price:
                self.db_object.start_price = kwargs['start_price']
            if kwargs['upper_price'] > self.db_object.upper_price:
                self.db_object.upper_price = kwargs['upper_price']
            del kwargs['start_price']
            del kwargs['upper_price']

            for prop_name, prop_value in kwargs.iteritems():
                if getattr(self.db_object, prop_name) != prop_value:
                    setattr(self.db_object, prop_name, prop_value)
                    self.is_dirty = True
        # pylint: disable=no-member
        if image_url and \
            (not self.db_object.image or self.db_object.image.original_url != image_url):
            img = Image(image_url)
            img.save()
            self.db_object.image = img.db_image
            self.is_dirty = True
        # pylint: enable=no-member
        if self.is_dirty:
            self.db_object.put()

    @classmethod
    def from_parsed_feed_item(cls, parsed_item):
        if not parsed_item.geo or not parsed_item.is_active:
            return

        _keywords = []
        _property_types = []
        for keyword in parsed_item.keywords:
            if keyword.lower() in [
                    'house',
                    'apartment',
                    'condo',
                    'cottage/cabin',
                    'duplex',
                    'flat',
                    'in-law',
                    'townhouse'
                ]:
                _property_types.append(keyword)
            else:
                _keywords.append(keyword)

        _price = parsed_item.price
        if (isinstance(_price, str) or isinstance(_price, unicode)) and \
            _price.startswith("$"):
            _price = _price[1:]

        property_listing = cls(
            title=parsed_item.title,
            body_html=parsed_item.posting_body,
            start_price=float(_price),
            upper_price=float(_price),
            address=parsed_item.address,
            neighborhood=parsed_item.neighborhood,
            city=parsed_item.city,
            state_code=parsed_item.state_code,
            postal_code=parsed_item.postal_code,
            country_code=parsed_item.country_code,
            geo=db.GeoPt(*parsed_item.geo),
            property_types=_property_types,
            keywords=_keywords,
            image_url=parsed_item.image_url
        )
        db_feed_item = _feed_item_from_url(parsed_item.feed_name, parsed_item.page_url)
        # pylint: disable=no-member
        if db_feed_item and db_feed_item.property_listing != property_listing.db_object:
            db_feed_item.property_listing = property_listing.db_object
            db_feed_item.put()
        # pylint: enable=no-member
        return property_listing

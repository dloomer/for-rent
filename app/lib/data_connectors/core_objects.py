# -*- coding: utf-8 -*-

# standard library imports
from google.appengine.ext import db

# local application/library specific imports
import app.models.core as core_models
from app.lib.data_connectors.image import Image

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
    def from_parsed_feed_item(cls, feed_item):
        feed_item.parse()
        if not feed_item.geo or not feed_item.is_active:
            return

        _keywords = []
        _property_types = []
        for keyword in feed_item.keywords:
            if keyword.lower() in [
                    'house',
                    'apartment',
                    'condo',
                    'cottage/cabin',
                    'duplex',
                    'flat',
                    'in-law'
                ]:
                _property_types.append(keyword)
            else:
                _keywords.append(keyword)

        _price_str = feed_item.price
        if _price_str.startswith("$"):
            _price_str = _price_str[1:]

        property_listing = cls(
            title=feed_item.title,
            body_html=feed_item.posting_body,
            start_price=float(_price_str),
            upper_price=float(_price_str),
            address=feed_item.address,
            neighborhood=feed_item.neighborhood,
            city=feed_item.city,
            state_code=feed_item.state_code,
            postal_code=feed_item.postal_code,
            country_code=feed_item.country_code,
            geo=db.GeoPt(*feed_item.geo),
            property_types=_property_types,
            keywords=_keywords,
            image_url=feed_item.image_url
        )
        feed_item_key_name = core_models.FeedItemCache.generate_key_name(
            feed_name=feed_item.feed_name,
            item_link=feed_item.page_url
        )
        db_feed_item = core_models.FeedItemCache.get_by_key_name(feed_item_key_name)
        # pylint: disable=no-member
        if db_feed_item and db_feed_item.property_listing != property_listing.db_object:
            db_feed_item.property_listing = property_listing.db_object
            db_feed_item.put()
        # pylint: enable=no-member
        return property_listing

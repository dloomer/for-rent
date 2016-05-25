# -*- coding: utf-8 -*-

# standard library imports
import datetime
import logging
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

def get_active_property_listings():
    return core_models.PropertyListing.all().filter("is_active = ", True).fetch(200)

def get_listing_source_items(db_property_listing):
    return db_property_listing.feeditemcache_set.fetch(200)

class PropertyListing(object):
    def __init__(self, db_object=None, image_url=None, **kwargs):
        if isinstance(kwargs['geo'], list):
            kwargs['geo'] = db.GeoPt(*kwargs['geo'])
        if db_object:
            self.db_object = db_object
            self.is_new = False
        else:
            self.db_object, self.is_new = core_models.PropertyListing \
                .get_or_insert_with_flag(create=kwargs['is_active'], **kwargs)
            if not self.db_object:
                # happens if 'create' parm to get_or_insert_with_flag is False,
                # and object didn't already exist. Nothing left to do.
                return

        self.is_dirty = False
        self.is_reactivated = False

        prev_active = False
        if not self.is_new:
            # special logic for pricing
            if kwargs['start_price'] < self.db_object.start_price:
                self.db_object.start_price = kwargs['start_price']
            if kwargs['upper_price'] > self.db_object.upper_price:
                self.db_object.upper_price = kwargs['upper_price']
            del kwargs['start_price']
            del kwargs['upper_price']

            # pylint: disable=no-member
            prev_active = self.db_object.is_active
            if kwargs.get('is_active'):
                for prop_name, prop_value in kwargs.iteritems():
                    if getattr(self.db_object, prop_name) != prop_value:
                        setattr(self.db_object, prop_name, prop_value)
                        self.is_dirty = True
            else:
                self.db_object.is_active = False

            if self.db_object.is_active != prev_active:
                if self.db_object.is_active:
                    self.db_object.inactive_since_date = None
                    self.is_reactivated = True
                else:
                    self.db_object.inactive_since_date = datetime.datetime.now()
                self.is_dirty = True
            # pylint: enable=no-member
        if image_url and \
            (not self.db_object.image or self.db_object.image.original_url != image_url):
            img = Image(image_url)
            img.save()
            self.db_object.image = img.db_image
            self.is_dirty = True
        if self.is_dirty:
            self.db_object.put()

    @classmethod
    def from_parsed_feed_items(cls, parsed_items, db_object=None):
        is_rejected = False
        geo = []
        title, body_html = "", ""
        start_price, upper_price = 0.0, 0.0
        address, neighborhood, city, state_code, postal_code, country_code = \
            "", "", "", "", "", ""
        _keywords, _property_types = [], []
        image_url = ""
        is_active = False
        user_urls = []

        for parsed_item in parsed_items:
            parsed_item.validate()
            is_rejected = is_rejected or parsed_item.is_rejected
            is_active = is_active or parsed_item.is_active
            user_urls.append(parsed_item.user_url)
            if not parsed_item.is_active:
                continue

            if parsed_item.geo:
                geo = parsed_item.geo
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
            if start_price == 0 or float(_price) < start_price:
                start_price = float(_price)
            if float(_price) > upper_price:
                upper_price = float(_price)
            title = title or parsed_item.title
            body_html = body_html or parsed_item.posting_body
            address = address or parsed_item.address
            neighborhood = neighborhood or parsed_item.neighborhood
            city = city or parsed_item.city
            state_code = state_code or parsed_item.state_code
            postal_code = postal_code or parsed_item.postal_code
            country_code = country_code or parsed_item.country_code
            image_url = image_url or parsed_item.image_url

        if is_rejected:
            if db_object:
                logging.info("Deleting property listing at URL(s) %s", user_urls)
                db_object.delete()
                for parsed_item in parsed_items:
                    db_feed_item = _feed_item_from_url(parsed_item.feed_name, parsed_item.page_url)
                    # pylint: disable=no-member
                    if db_feed_item and \
                        core_models.FeedItemCache.property_listing.get_value_for_datastore(
                                db_feed_item
                            ) is not None:
                        db_feed_item.property_listing = None
                        db_feed_item.put()
                    # pylint: enable=no-member
            return

        if db_object and not is_active:
            logging.info("Inactivating property listing at URL(s) %s", user_urls)
        elif not geo:
            # require geo when we're not inactivating something.
            return

        geo_pt = db.GeoPt(*geo) if geo else None

        # pylint: disable=no-value-for-parameter
        property_listing = cls(
            title=title,
            body_html=body_html,
            start_price=start_price,
            upper_price=upper_price,
            address=address,
            neighborhood=neighborhood,
            city=city,
            state_code=state_code,
            postal_code=postal_code,
            country_code=country_code,
            geo=geo_pt,
            property_types=_property_types,
            keywords=_keywords,
            image_url=image_url,
            is_active=is_active,
            db_object=db_object
        )
        # pylint: enable=no-value-for-parameter
        if not property_listing.db_object:
            # some requirement wasn't met above, so pretend we were never here.
            return

        for parsed_item in parsed_items:
            db_feed_item = _feed_item_from_url(parsed_item.feed_name, parsed_item.page_url)
            # pylint: disable=no-member
            if db_feed_item and db_feed_item.property_listing != property_listing.db_object:
                db_feed_item.property_listing = property_listing.db_object
                db_feed_item.put()
            # pylint: enable=no-member

        return property_listing

    @classmethod
    def from_parsed_feed_item(cls, parsed_item, db_object=None):
        return cls.from_parsed_feed_items([parsed_item], db_object=db_object)

from google.appengine.ext import db

from app.lib.utils import string_utils

def concat_key_elements(elements):
    return '|'.join(elements)

class BaseModel(db.Model):
    @classmethod
    def generate_key_name(cls, **kwargs):
        if 'key_name' in kwargs:
            return kwargs['key_name']

    @classmethod
    def get_or_insert_by_values(cls, **kwargs):
        return cls.get_or_insert(cls.generate_key_name(**kwargs), **kwargs)

class PropertyListing(BaseModel):
    city = db.StringProperty(required=True)
    address = db.StringProperty(required=True)
    property_types = db.StringListProperty()

    @classmethod
    def generate_key_name(cls, **kwargs):
        key_name = super(PropertyListing, cls).generate_key_name(**kwargs)
        if not key_name:
            key_name = concat_key_elements([
                string_utils.slugify(kwargs['city']),
                string_utils.slugify(kwargs['address'])
            ])
        return key_name

class FeedItem(BaseModel):
    feed_name = db.StringProperty(required=True)
    item_link = db.StringProperty(required=True)
    create_date = db.DateTimeProperty(auto_now_add=True, indexed=False)
    property_listing = db.ReferenceProperty(PropertyListing, indexed=False)

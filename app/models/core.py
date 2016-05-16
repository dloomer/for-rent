from google.appengine.ext import db

from app.lib.utils import string_utils

def concat_key_elements(elements):
    return '|'.join(elements)

class SerializedDataProperty(db.Property):
    def get_value_for_datastore(self, model_instance):
        value = super(SerializedDataProperty, self).get_value_for_datastore(model_instance)
        return db.Blob(pickle.dumps(value))

    def make_value_from_datastore(self, value):
        if value is None:
            return None
        return pickle.loads(value)

    def default_value(self):
        if self.default is None:
            return None
        else:
            return copy.deepcopy(super(SerializedDataProperty, self).default_value())

    def empty(self, value):
        return value is None

class DictProperty(SerializedDataProperty):
    data_type = dict

    def make_value_from_datastore(self, value):
        if value is None:
            return dict()
        return super(DictProperty, self).make_value_from_datastore(value)

    def default_value(self):
        if self.default is None:
            return dict()
        else:
            return copy.deepcopy(super(DictProperty, self).default_value())

    def validate(self, value):
        if not isinstance(value, dict):
            raise db.BadValueError('Property %s needs to be convertible '
                                                 'to a dict instance (%s) of class dict' % (self.name, value))
        return super(DictProperty, self).validate(value)

class BaseModel(db.Model):
    @classmethod
    def generate_key_name(cls, **kwargs):
        if 'key_name' in kwargs:
            return kwargs['key_name']

    @classmethod
    def get_or_insert_by_values(cls, **kwargs):
        return cls.get_or_insert(cls.generate_key_name(**kwargs), **kwargs)

    @classmethod
    def get_or_insert_with_flag(cls, **kwargs):
        @db.transactional
        def _tx():
            key_name = cls.generate_key_name(**kwargs)
            entity = cls.get_by_key_name(
                key_name
            )
            if entity:
                return entity, False
            entity = cls(key_name=key_name, **kwargs)
            entity.put()
            return entity, True
        return _tx()

class PropertyListing(BaseModel):
    title = db.StringProperty(required=True, indexed=False)
    city = db.StringProperty(required=True)
    neighborhood = db.StringProperty()
    state_code = db.StringProperty()
    postal_code = db.StringProperty()
    country_code = db.StringProperty()
    start_price = db.FloatProperty()
    upper_price = db.FloatProperty()
    address = db.StringProperty(required=True)
    property_types = db.StringListProperty(indexed=False)
    keywords = db.StringListProperty(indexed=False)
    geo = db.GeoPtProperty(required=True)
    is_active = db.BooleanProperty(required=True, default=True)
    create_date = db.DateTimeProperty(auto_now_add=True, indexed=False)
    # image
    # job to confirm active

    @classmethod
    def generate_key_name(cls, **kwargs):
        key_name = super(PropertyListing, cls).generate_key_name(**kwargs)
        if not key_name:
            key_name = concat_key_elements([
                str(kwargs['geo'].lat),
                str(kwargs['geo'].lon)
            ])
        return key_name

class FeedItemCache(BaseModel):
    feed_name = db.StringProperty(required=True)
    item_link = db.StringProperty(required=True)
    create_date = db.DateTimeProperty(auto_now_add=True, indexed=False)
    property_listing = db.ReferenceProperty(PropertyListing, indexed=False)

    @classmethod
    def generate_key_name(cls, **kwargs):
        key_name = super(FeedItemCache, cls).generate_key_name(**kwargs)
        if not key_name:
            key_name = concat_key_elements([
                kwargs['feed_name'],
                kwargs['item_link']
            ])
        return key_name

class InboxItem(BaseModel):
    user_name = db.StringProperty(required=True)
    property_listing = db.ReferenceProperty(PropertyListing)
    property_listing_metadata = DictProperty()
    feed_names = db.StringListProperty(indexed=False)
    is_read = db.BooleanProperty()
    is_in_trash = db.BooleanProperty()
    is_faved = db.BooleanProperty()
    create_date = db.DateTimeProperty(auto_now_add=True, indexed=False)

import urllib

from google.appengine.ext.blobstore import BlobReader
from google.appengine.api import mail

# local application/library specific imports
from app.lib.data_connectors import feed_config_connector

def send_property_notification(property_listing, item_url):
    recipients_config = feed_config_connector.get_alert_recipients()
    recipients = ["%s <%s>" % (_['name'], _['email']) for _ in recipients_config]

    property_type_map = {
        'apartment': "Apartment",
        'condo': "Condo",
        'cottage/cabin': "Cottage/Cabin",
        'duplex': "Duplex",
        'flat': "Flat",
        'house': "House",
        'in-law': "In-Law",
        'townhouse': "Townhouse"
    }
    # TODO: use app_identity
    sender_address = "Rental Bot <noreply@for-rent-1305.appspotmail.com>"
    property_type = property_listing.property_types[0] \
        if property_listing.property_types else "Property"
    property_type_description = property_type_map.get(property_type, property_type)
    formatted_address = "%s, %s, %s %s" % (
        property_listing.address,
        property_listing.city,
        property_listing.state_code,
        property_listing.postal_code
    )
    geo = property_listing.geo
    subject = "%s in %s (%s)" % (
        property_type_description,
        property_listing.neighborhood,
        property_listing.address
    )
    message = mail.EmailMessage(
        sender=sender_address,
        subject=subject,
        to=recipients
    )

    message.body = item_url
    message.html = """<a href="{}">{}</a><br/>
<br/>
<a href="https://www.google.com/maps/place/{}/@{}">Google Maps</a><br/>


""".format(
    item_url,
    property_listing.title.encode('utf-8'),
    urllib.quote_plus(formatted_address),
    "%s,%s" % (geo.lat, geo.lon)
)
    blob_reader = BlobReader(property_listing.image.original_jpeg_blob_key)
    message.attachments=[("property.jpg", blob_reader.read())]
    message.send()

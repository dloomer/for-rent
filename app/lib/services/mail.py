from google.appengine.api import mail

def send_property_notification(property_listing, item_url):
    sender_address = "Rental Bot <noreply@for-rent-1305.appspotmail.com>"
    property_type = property_listing.property_types[0]
    subject = "%s in %s" % (property_type, property_listing.neighborhood)
    message = mail.EmailMessage(
        sender=sender_address,
        subject=subject,
        to=["Dave Loomer <dloomer@gmail.com>", "Bitchypants <lesley.babb@gmail.com>"]
    )

    message.body = item_url
    message.send()

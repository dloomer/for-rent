# -*- coding: utf-8 -*-

# standard library imports
from StringIO import StringIO
from urlparse import urlparse

from PIL import Image as PIL_Image
from PIL import ImageFile

from google.appengine.ext import blobstore, db
from google.appengine.api import app_identity, urlfetch
from google.appengine.api.urlfetch_errors import ConnectionClosedError, DeadlineExceededError

try:
    import cloudstorage as gcs
except ImportError:
    import third_party.cloudstorage as gcs

# local application/library specific imports
import app.models.core as core_models
from app.lib.data_connectors import feed_config_connector

COMPRESSION_SETTINGS = {
    'original': {
        'file_shortname': "o",
        'quality': 80,
        'library_used': "PIL",
        'progressive': True,
        'optmize': True
    },
    'small': {
        'file_shortname': "t",
        'quality': 80,
        'thumbnail_dimensions': (150, 1000),
        'library_used': "PIL",
        'progressive': True,
        'optmize': True
    },
    'retina_small': {
        'file_shortname': "rt",
        'quality': 60,
        'thumbnail_dimensions': (300, 2000),
        'library_used': "PIL",
        'progressive': True,
        'optmize': True
    }
}

def _get_image_info(data):
    import struct

    data = str(data)
    size = len(data)
    height = -1
    width = -1
    content_type = ''
    # handle GIFs
    if (size >= 10) and data[:6] in ('GIF87a', 'GIF89a'):
        # Check to see if content_type is correct
        content_type = 'image/gif'
        width_s, height_s = struct.unpack("<HH", data[6:10])
        width = int(width_s)
        height = int(height_s)
    # See PNG 2. Edition spec (http://www.w3.org/TR/PNG/)
    # Bytes 0-7 are below, 4-byte chunk length, then 'IHDR'
    # and finally the 4-byte width, height
    elif ((size >= 24) and data.startswith('\211PNG\r\n\032\n')
          and (data[12:16] == 'IHDR')):
        content_type = 'image/png'
        width_s, height_s = struct.unpack(">LL", data[16:24])
        width = int(width_s)
        height = int(height_s)
    # Maybe this is for an older PNG version.
    elif (size >= 16) and data.startswith('\211PNG\r\n\032\n'):
        # Check to see if we have the right content type
        content_type = 'image/png'
        width_s, height_s = struct.unpack(">LL", data[8:16])
        width = int(width_s)
        height = int(height_s)
    # handle JPEGs
    elif (size >= 2) and data.startswith('\377\330'):
        content_type = 'image/jpeg'
        jpeg = StringIO(data)
        jpeg.read(2)
        bytes_ = jpeg.read(1)
        try:
            while bytes_ and ord(bytes_) != 0xDA:
                while ord(bytes_) != 0xFF:
                    bytes_ = jpeg.read
                while ord(bytes_) == 0xFF:
                    bytes_ = jpeg.read(1)
                if ord(bytes_) >= 0xC0 and ord(bytes_) <= 0xC3:
                    jpeg.read(3)
                    height_s, width_s = struct.unpack(">HH", jpeg.read(4))
                    break
                else:
                    jpeg.read(int(struct.unpack(">H", jpeg.read(2))[0])-2)
                bytes_ = jpeg.read(1)
            width = int(width_s)
            height = int(height_s)
        except struct.error:
            pass
        except ValueError:
            pass
    return content_type, width, height

def _save_gcs_object(data, file_name, content_type='application/octet-stream', options=None):
    bucket_name = app_identity.get_default_gcs_bucket_name()

    if not file_name.startswith("/" + bucket_name):
        file_name = "/" + bucket_name + file_name

    # Open the file and write to it
    for _ in range(3):
        try:
            with gcs.open(file_name, 'w', content_type=content_type, options=options) as file_:
                file_.write(data)
            break
        except gcs.errors.ServerError:
            pass

    # Blobstore API requires extra /gs to distinguish against blobstore files.
    blobstore_filename = '/gs' + file_name
    blob_key = blobstore.create_gs_key(blobstore_filename)
    return blob_key

class Image(object):
    def _url_for_urlfetch(self, url):
        parsed = urlparse(url)

        images_hostname_proxy = None
        if parsed.netloc.lower() == "craigslist.org" or \
           parsed.netloc.lower().endswith(".craigslist.org"):
            images_hostname_proxy = \
                self.images_hostname_proxies.get('craigslist')

        if images_hostname_proxy:
            proxied_url = \
                parsed.scheme + '://' + \
                images_hostname_proxy + \
                parsed.path + \
                ('?' + parsed.query if parsed.query else '')
            return proxied_url
        else:
            return url

    def __init__(self, source_url):
        self.images_hostname_proxies = feed_config_connector.get_images_hostname_proxies()
        self.source_url = source_url
        for _ in range(3):
            try:
                self.img_data = urlfetch.fetch(
                    self._url_for_urlfetch(self.source_url),
                    deadline=20
                ).content
                break
            except ConnectionClosedError:
                pass
            except DeadlineExceededError:
                pass
        self.db_image = None

        handmade_key = db.Key.from_path("Image", 1)
        self._allocated_image_key = \
            db.Key.from_path('Image', list(db.allocate_ids(handmade_key, 1))[0])

    def _save_gcs_image(self, img, mime_type, image_size):
        size_in_pixels = img.size[0] * img.size[1]
        import logging
        from google.appengine.api import runtime
        from google.appengine.api import logservice
        logservice.AUTOFLUSH_ENABLED = False
        logging.debug("image size=%s" % size_in_pixels)
        logservice.flush()

        if size_in_pixels > 12 * (10**6):
            del img
            raise ValueError("Image too large (%s pixels)", size_in_pixels)
        if mime_type.lower().startswith("image/"):
            format_ = mime_type[6:].upper()
        else:
            raise ValueError("Unexpected MIME type %s" % mime_type)

        settings = COMPRESSION_SETTINGS[image_size]

        ImageFile.MAXBLOCK = 2**20
        img_io = StringIO()

        if settings.get('thumbnail_dimensions'):
            img = img.copy()
            img.thumbnail(settings['thumbnail_dimensions'], PIL_Image.ANTIALIAS)
            img = img.convert('RGB')

        img.save(
            img_io,
            format_,
            quality=settings['quality'],
            optimize=settings['quality'],
            progressive=settings['progressive']
        )
        img_data = img_io.getvalue()
        _, saved_width, saved_height = _get_image_info(img_data)
        img_io.close()

        file_name = "/images/%s/%s.jpg" % (
            self._allocated_image_key.id(),
            settings['file_shortname']
        )
        blob_key = _save_gcs_object(
            img_data,
            file_name,
            content_type=mime_type,
            options={'x-goog-acl': 'public-read'}
        )
        return blob_key, img_data, [saved_width, saved_height]

    def save(self):
        file_ = StringIO(self.img_data)
        img = PIL_Image.open(file_)
        original_blob_key, _, orig_dimensions = \
            self._save_gcs_image(
                img,
                "image/jpeg",
                'original'
            )
        small_blob_key, _, small_dimensions = \
            self._save_gcs_image(
                img,
                "image/jpeg",
                'small'
            )
        retina_small_blob_key, _, retina_small_dimensions = \
            self._save_gcs_image(
                img,
                "image/jpeg",
                'retina_small'
            )

        db_image = core_models.Image(
            key=self._allocated_image_key,
            original_url=self.source_url,
            small_jpeg_blob_key=small_blob_key,
            original_jpeg_blob_key=original_blob_key,
            retina_small_jpeg_blob_key=retina_small_blob_key,
            small_jpeg_dimensions=small_dimensions,
            original_jpeg_dimensions=orig_dimensions,
            retina_small_jpeg_dimensions=retina_small_dimensions,
        )
        db_image.compression_metadata = COMPRESSION_SETTINGS
        db_image.put()

        self.db_image = db_image

# -*- coding: utf-8 -*-

"""
    Routes are setup in routes.py and added in main.py
"""
# standard library imports
import logging
import re

# related third party imports
import webapp2
from google.appengine.ext.webapp import template

import os, datetime
import copy

# local application/library specific imports
import app.models.core as core_models

from app.lib.utils import string_utils

class BaseHandler(webapp2.RequestHandler):
    def get(self):
        from google.appengine.api import users

        if os.environ['SERVER_SOFTWARE'].find('Development') < 0:
            if not users.get_current_user():
                self.redirect(users.create_login_url(self.request.path))

    def render_template(self, filename, **template_args):
        path = os.path.join(os.path.dirname(__file__), '..', '..', 'templates', filename)
        
        # update template_args with standard arguments here.

        logging.debug("self.response.write(template.render(path, template_args))")
        self.response.write(template.render(path, template_args))
        logging.debug("end code")

class HomeRequestHandler(BaseHandler):
    def get(self):
        super(HomeRequestHandler, self).get()

        params = {}
        logging.debug("headers=%s" % self.request.headers)

        #return self.render_template('home.html', **params)

        # import app.lib.services.mail as mail
        # import app.models.core as core_models

        # property_listing = core_models.PropertyListing.get_by_key_name('47.6057333|-122.3161506')
        # feed_item = property_listing.feeditemcache_set.get()
        # mail.send_property_notification(property_listing, feed_item.item_link)

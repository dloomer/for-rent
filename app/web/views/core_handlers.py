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

template.register_template_library("app.web.views.core_template_library") 

class BaseHandler(webapp2.RequestHandler):
    # If we want, we can put in some automatic caching by overriding dispatch()
    '''
    def dispatch(self):
        """Dispatches the request.

        This will first check if there's a handler_method defined in the
        matched route, and if not it'll use the method correspondent to the
        request method (``get()``, ``post()`` etc).
        """
        request = self.request
        method_name = request.route.handler_method
        if not method_name:
            method_name = _normalize_handler_method(request.method)

        method = getattr(self, method_name, None)
        if method is None:
            # 405 Method Not Allowed.
            # The response MUST include an Allow header containing a
            # list of valid methods for the requested resource.
            # http://www.w3.org/Protocols/rfc2616/rfc2616-sec10.html#sec10.4.6
            valid = ', '.join(_get_handler_methods(self))
            self.abort(405, headers=[('Allow', valid)])

        # The handler only receives *args if no named variables are set.
        args, kwargs = request.route_args, request.route_kwargs
        if kwargs:
            args = ()

        try:
            return method(*args, **kwargs)
        except Exception, e:
            return self.handle_exception(e, self.app.debug)
    '''
    def render_template(self, filename, **template_args):
        path = os.path.join(os.path.dirname(__file__), '..', '..', 'templates', filename)
        
        # update template_args with standard arguments here.

        template_args.update({
        })

        self.response.write(template.render(path, template_args))

class ArtistRequestHandler(BaseHandler):
    def get(self, slug):
        '''
        if os.environ['SERVER_SOFTWARE'].startswith('Dev'):
            from google.appengine.ext.remote_api import remote_api_stub
            import getpass

            def auth_func():
                return ('mnlivedotnet@gmail.com', '****')

            remote_api_stub.ConfigureRemoteApi(None, '/_ah/remote_api', auth_func,
                                           'mnlive-hrd.appspot.com')
        '''

        artist_key = slug.replace("-", " ")
        artist = core_models.Artist.get_by_key_name(artist_key)
        params = {'artist': artist}
        if artist.cached_image_data.get('o_dim'):
            params['artist_image_height_pct'] = int(round(float(artist.cached_image_data['o_dim'][1]) / float(artist.cached_image_data['o_dim'][0]) * 100.0))
        params['artist_supporting_data'] = artist.get_cached_supporting_data()
        return self.render_template('artist.html', **params)

# -*- coding: utf-8 -*-

"""
    Routes are setup in routes.py and added in main.py
"""
# standard library imports
import logging
import re
# related third party imports
import webapp2

# local application/library specific imports
import app.models as models

class HomeRequestHandler(webapp2.RequestHandler):
    """
    Handler to show the home page
    """

    def get(self):
        """ Returns a simple HTML form for home """
        params = {}
        #return self.render_template('boilerplate_home.html', **params)

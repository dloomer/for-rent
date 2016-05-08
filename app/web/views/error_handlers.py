
"""
    Routes are setup in routes.py and added in main.py
"""
# standard library imports
import logging
import re
# related third party imports
import webapp2
import datetime

from google.appengine.ext import db
from google.appengine.ext.webapp import template

import os
import json

def handle_404(request, response, exception):
    params = {}
    path = os.path.join(os.path.dirname(__file__), '..', '..', 'templates', '404.html')
    logging.debug("request.headers=%s" % request.headers)
    response.write(template.render(path, params))

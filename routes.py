"""
Using redirect route instead of simple routes since it supports strict_slash
Simple route: http://webapp-improved.appspot.com/guide/routing.html#simple-routes
RedirectRoute: http://webapp-improved.appspot.com/api/webapp2_extras/routes.html#webapp2_extras.routes.RedirectRoute
"""

from webapp2_extras.routes import RedirectRoute
from app.web.views import user_handlers as user_handlers
from app.web.views import core_handlers as core_handlers
from app.web.views import error_handlers as error_handlers

secure_scheme = 'https'

_routes = [
    (r'/show/(.*)', core_handlers.ShowRequestHandler),
    (r'/artist/(.*)', core_handlers.ArtistRequestHandler),
    RedirectRoute('/', core_handlers.HomeRequestHandler, name='home', strict_slash=True),
]

def get_routes():
    return _routes

def add_routes(app):
    if app.debug:
        secure_scheme = 'http'
    for r in _routes:
        app.router.add(r)
    
    app.error_handlers[404] = error_handlers.handle_404
    #app.error_handlers[500] = handle_500

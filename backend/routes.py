"""
Using redirect route instead of simple routes since it supports strict_slash
Simple route: http://webapp-improved.appspot.com/guide/routing.html#simple-routes
RedirectRoute: http://webapp-improved.appspot.com/api/webapp2_extras/routes.html#webapp2_extras.routes.RedirectRoute
"""

from webapp2_extras.routes import RedirectRoute
from backend.web.views import batch_handlers as batch_handlers
from backend.web.views import task_handlers as task_handlers

secure_scheme = 'https'

_routes = [
    RedirectRoute(
        '/batch/load_feed_data',
        batch_handlers.LoadFeedDataRequestHandler,
        name='load_feed_data',
        strict_slash=True
    ),
    RedirectRoute(
        '/task/process_data_feed_entries',
        task_handlers.DataFeedEntriesHandler,
        name='process_data_feed_entries',
        strict_slash=True
    ),
]

def get_routes():
    return _routes

def add_routes(app):
    if app.debug:
        secure_scheme = 'http'
    for r in _routes:
        app.router.add(r)

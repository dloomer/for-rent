import os

import yaml

FEEDS_PATH = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'feeds.yaml')

def get_feed_config():
    _config = None
    with open(FEEDS_PATH, 'r') as stream:
        _config = yaml.load(stream)
    return _config

def get_feeds_map(feed_config=None):
    feeds_map = {}
    if not feed_config:
        feed_config = get_feed_config()
    feeds = feed_config['feeds']
    for feed in feeds:
        feeds_map[feed['name']] = feed
    return feeds_map

import os
import sys

# Enable third-party imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'third_party'))
remoteapi_CUSTOM_ENVIRONMENT_AUTHENTICATION = ('HTTP_X_APPENGINE_INBOUND_APPID',['mn-live'])

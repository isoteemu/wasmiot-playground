"""
Zeroconf client for webthings.

This module provides a client for the webthings protocol. It uses zeroconf
to discover webthings and then uses the webthings protocol to communicate
with them.
"""

import logging
import socket
import threading
import time
import urllib.parse

import zeroconf

from . import protocol

_LOGGER = logging.getLogger(__name__)

# The service type for webthings.
SERVICE_TYPE = '_webthing._tcp.local.'

# The timeout for webthing discovery.
DISCOVERY_TIMEOUT = 5

# The timeout for webthing connections.
CONNECTION_TIMEOUT = 5

# The timeout for webthing requests.
REQUEST_TIMEOUT = 5

# The number of times to retry a request.
REQUEST_RETRIES = 3

# The number of seconds to wait between retries.
REQUEST_RETRY_DELAY = 1

class WebThingClient:
    """A client for webthings."""

    def __init__(self, zeroconf_instance=None):
        """Initialize the client."""
        if zeroconf_instance is None:
            zeroconf_instance = zeroconf.Zeroconf()
        self.zeroconf = zeroconf_instance

    def discover(self, timeout=DISCOVERY_TIMEOUT):
        """Discover webthings."""
        browser = zeroconf.ServiceBrowser(self.zeroconf, SERVICE_TYPE,
                                          listener=WebThingListener())
        time.sleep(timeout)
        browser.cancel()

        return browser.services.values()

    def connect(self, thing, timeout=CONNECTION_TIMEOUT):
        """Connect to a webthing."""
        info = self.zeroconf.get_service_info(SERVICE_TYPE, thing)
        if info is None:
            return None

        host = socket.inet_ntoa(info.address)
        port = info.port
        path = urllib.parse.urlparse(info.properties[b'path']).path

        return protocol.WebThingConnection(host, port, path, timeout)

    def request(self, thing, request, timeout=REQUEST_TIMEOUT,
                retries=REQUEST_RETRIES, retry_delay=REQUEST_RETRY_DELAY):
        """Make a request to a webthing."""
        for _ in range(retries):
            try:
                with self.connect(thing, timeout) as conn:
                    return conn.request(request)
            except (ConnectionError, socket.timeout):
                pass

            time.sleep(retry_delay)

        return None


class WebThingListener(zeroconf.ServiceListener):
    """A zeroconf listener for webthings."""

    def __init__(self):
        """
        Initialize the listener.
        
        .. todo:: Use ServiceRegistry instead of a dict.
        """

        self.services = {}

    def add_service(self, zeroconf, service_type, name):
        """Add a service."""
        info = zeroconf.get_service_info(service_type, name)
        if info is None:
            return

        self.services[name] = info

    def remove_service(self, zeroconf, service_type, name):
        """Remove a service."""
        self.services.pop(name, None)

    def update_service(self, zeroconf, service_type, name):
        """Update a service."""
        self.add_service(zeroconf, service_type, name)


class WebThingClientDiscovery(threading.Thread):
    """A thread for discovering webthings."""

    def __init__(self, client, callback):
        """Initialize the thread."""
        super().__init__()
        self.client = client
        self.callback = callback

    def run(self):
        """Run the thread."""
        things = self.client.discover()
        self.callback(things)


class WebThingClientRequest(threading.Thread):
    """A thread for making a request to a webthing."""

    def __init__(self, client, thing, request, callback):
        """Initialize the thread."""
        super().__init__()
        self.client = client
        self.thing = thing
        self.request = request
        self.callback = callback

    def run(self):
        """Run the thread."""
        response = self.client.request(self.thing, self.request)
        self.callback(response)


class WebThingClientConnection(threading.Thread):
    """A thread for connecting to a webthing."""

    def __init__(self, client, thing, callback):
        """Initialize the thread."""
        super().__init__()
        self.client = client
        self.thing = thing
        self.callback = callback

    def run(self):
        """Run the thread."""
        conn = self.client.connect(self.thing)
        self.callback(conn)



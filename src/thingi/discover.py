"""
Library for discovering Webthings.

Implements the Webthing Discovery API as described in the Webthing API
specification, but omits the TDD (Thing Description Directory) part.

.. todo:: Implement the TDD of the Webthing Discovery API.

"""

import logging
from typing import TypedDict
import httpx
import sentry_sdk

import zeroconf

logger = logging.getLogger(__name__)


class NodeInfo(TypedDict, total=False):
    """
    Node info.
    """


class HTTPClientAdapter(httpx.Client):
    pass


def get_service_info(zc: zeroconf.Zeroconf, type_, name):
    """
    Get service info.

    Uses the zeroconf instance to get the service info, and then fetches
    additional info from the webthing advertised URL.
    """
    service_info = zc.get_service_info(type_, name)
    # TODO: fetch additional info
    return service_info


async def explore_service_info(si: zeroconf.ServiceInfo):
    """
    Explore service info.

    Uses the zeroconf service info to explore the webthing advertised URL.
    
    .. todo:: Make it async.
    """

    # Select adapter based on schema and protocol    
    adapter = create_request_adapter(si)

    properties = {
        'td': '/.well-known/thing-description',
    }

    ...
    

def create_request_adapter(si: zeroconf.ServiceInfo):
    """
    Create a request adapter.

    Creates a rest request adapter for the current protocol and scheme.
    
    .. todo:: Implement CoAP and udp.
    """

    match si.properties:
        case {"type": "Directory"}:
            raise NotImplementedError("Directory not implemented yet")
        case {"scheme": b"coap" | b"coaps" | b"coap+tcp" | b"coaps+tcp"}:
            raise NotImplementedError("CoAP not implemented yet")
        case {"scheme": b"http" | b"https"}:
            return HTTPClientAdapter()
        case {"scheme": None}:
            si.properties["scheme"] = b"http"
            return HTTPClientAdapter()
        case _:
            raise ValueError("Unknown scheme or protocol")


class WebThingListener(zeroconf.ServiceListener):
    """A zeroconf listener for webthings."""

    def __init__(self):
        """Initialize the listener."""
        self.services = {}

    def add_service(self, zeroconf: zeroconf.Zeroconf, service_type, name):
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


class Discover():
    """A class for discovering webthings."""
    
    TYPE: str = "_wot._tcp.local."

    def __init__(self, zeroconf_instance=None):
        """Initialize the discover class."""
        self.zc = zeroconf_instance or zeroconf.Zeroconf()
        self.registry = {}
        self.listener = WebThingListener()

    def discover(self, timeout=5):
        """Discover webthings."""
        self.zc.add_service_listener(self.TYPE, self.listener)
        return self.listener.services

    def close(self):
        """Close the zeroconf instance."""
        self.zc.remove_service_listener(self.listener)
        self.zc.close()

    async def scan(self, timeout=5):
        # Send ServiceInfo request
        si = zeroconf.ServiceInfo(self.TYPE, self.TYPE)



if __name__ == "__main__":
    discover = Discover()

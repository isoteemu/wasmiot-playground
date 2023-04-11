"""
Library for discovering Webthings.

Implements the Webthing Discovery API as described in the Webthing API
specification, but omits the TDD (Thing Description Directory) part.

.. todo:: Implement the TDD of the Webthing Discovery API.

"""

import logging
import requests

import zeroconf

logger = logging.getLogger(__name__)


class HTTPClient(requests.Session):
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


def explore_service_info(si: zeroconf.ServiceInfo):
    """
    Explore service info.

    Uses the zeroconf service info to explore the webthing advertised URL.
    
    .. todo:: Make it async.
    """

    # Select adapter based on schema and protocol    
    adapter = create_request_adapter(si)

    properties = {
        'td': 
    }
    

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
            return HTTPClient()
        case {"scheme": None}:
            si.properties["scheme"] = b"http"
            return HTTPClient()
        case _:
            raise ValueError("Unknown scheme or protocol")


class WebThingListener(zeroconf.ServiceListener):
    """A zeroconf listener for webthings."""

    def __init__(self):
        """Initialize the listener."""
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


if __name__ == "__main__":
    import asyncio
    import time

    listener = do_discover()
        
    from time import sleep
    sleep(10)


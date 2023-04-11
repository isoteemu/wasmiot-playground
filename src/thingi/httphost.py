import socket
from typing import Tuple
import click
from flask import Flask
from werkzeug.serving import get_sockaddr, select_address_family
from zeroconf import ServiceInfo, Zeroconf

from .utils import get_hostname


def get_listening_address(app: Flask) -> Tuple[str, int]:
    """
    Return the address Flask application is listening.
    TODO: Does not detect if listening on multiple addresses.
    """

    # Copied from flask/app.py and werkzeug.service how it determines address,
    # as serving address is not stored. By default flask uses request iformation
    # for this, but we can't rely on that.

    host = None
    port = None

    # Try guessing from server name, default path for flask.
    server_name = app.config.get("SERVER_NAME")
    if server_name:
        host, _, port = server_name.partition(":")
    port = port or app.config.get("PORT") or 5000

    # Fallback
    if not host:
        # From https://stackoverflow.com/questions/166506/finding-local-ip-addresses-using-pythons-stdlib/28950776#28950776
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0)
        try:
            s.connect(("10.255.255.255", 1))
            host, *_ = s.getsockname()
        except Exception:
            host = "0.0.0.0"
        finally:
            s.close()

    address_family = select_address_family(host, port)
    server_address = get_sockaddr(host, int(port), address_family)
    if isinstance(server_address, str):
        raise NotImplementedError("Unix sockets not supported")

    return server_address


def init_zeroconf(app: Flask):
    server_name = app.config['SERVER_NAME'] or get_hostname()
    host, port = get_listening_address(app)

    properties={
        'path': '/',
        'tls': 1 if app.config.get("PREFERRED_URL_SCHEME") == "https" else 0,
    }

    service_info = ServiceInfo(
        type_='_wot._tcp.local.',
        name=f"{app.name}._wot._tcp.local.",
        addresses=[socket.inet_aton(host)],
        port=port,
        properties=properties,
        server=f"{server_name}.local.",
    )

    app.extensions['wot_zeroconf'] = Zeroconf()
    app.extensions['wot_zeroconf'].register_service(service_info)
    
    return app.extensions['wot_zeroconf']


def create_app() -> Flask:
    app = Flask(__name__)

    init_zeroconf(app)
    
    return app


@click.command()
@click.option('--host', default=socket.gethostname())
@click.option('--port', default=5000, type=int)
@click.option('--ssl-cert', default=None, type=click.Path(exists=True, dir_okay=False))
@click.option('--ssl-key', default=None, type=click.Path(exists=True, dir_okay=False))
def run(host, port, ssl_cert, ssl_key):
    app = create_app()
    app.run(host=host, port=port, use_reloader=False)


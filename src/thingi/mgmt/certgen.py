from typing import TypeVar, overload
import click
from werkzeug.serving import generate_adhoc_ssl_pair
from cryptography.hazmat.primitives import serialization

from pathlib import Path

from thingi.utils import get_hostname
from thingi.settings import Settings

from thingi.mgmt.cli import cli

from io import IOBase

from multipledispatch import dispatch

@dispatch(str, str, (str, ))
def generate_cert(key_file: str, cert_file: str, host=get_hostname()) -> tuple[str, str]:  # type: ignore
    k, c = generate_cert(Path(key_file), Path(cert_file), host)  # type: ignore
    return str(k), str(c)

@dispatch(Path, Path, (str, ))
def generate_cert(key_file: Path, cert_file: Path, host=get_hostname()) -> tuple[Path, Path]:  # type: ignore

    key_file.parent.mkdir(0o700, parents=True, exist_ok=True)
    cert_file.parent.mkdir(0o700, parents=True, exist_ok=True)
    
    with key_file.open("wb") as key_fd, cert_file.open("wb") as cert_fd:
        generate_cert(key_fd, cert_fd, host)

    return key_file, cert_file

@dispatch(IOBase, IOBase, (str, ))
def generate_cert(key_file: IOBase, cert_file: IOBase, host=get_hostname()) -> tuple[IOBase, IOBase]:    
    """
    Generate a self-signed certificate and key pair.
    
    Code adapted from Werkzeug's `generate_adhoc_ssl_pair` function.
    """

    cn = f"*.{host}/CN={host}"

    cert, key = generate_adhoc_ssl_pair(cn)

    key_file.write(key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ))

    cert_file.write(cert.public_bytes(serialization.Encoding.PEM))

    return key_file, cert_file


@cli.command()
@click.option('--key-file', '-k', 'key_file', type=click.Path(file_okay=True, writable=True))
@click.option('--cert-file', '-c', 'cert_file', type=click.Path(file_okay=True, writable=True))
@click.option('--host', '-h', 'host', default=get_hostname())
def certgen(key_file, cert_file, host):
    """
    Generate a self-signed certificate for a host.
    """

    settings = Settings()
    if key_file is None:
        key_file = settings.CERT_KEY_FILE or Path.cwd() / "cert.key"
    if cert_file is None:
        cert_file = settings.CERT_CRT_FILE or Path.cwd() / "cert.crt"

    key_file = Path(key_file)
    cert_file = Path(cert_file)

    click.echo(f"Generating certificate for {host}...")
    generate_cert(key_file, cert_file, host)
    click.echo(f"Certificate generated in {key_file} and {cert_file}.")

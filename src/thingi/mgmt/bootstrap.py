"""
Management console boot functions

"""

# TODO: Make this all as a class

# Registry of bootstrap functions
import asyncio
import logging
import os
from pathlib import Path
from random import randint

from thingi.init import Init, Skipped, Status

logger = logging.getLogger(__name__)
initrc = Init()

@initrc.rc
async def load_settings(current_app):
    """Loading Settings"""
    from thingi.settings import Settings

    current_app.settings = Settings()

    return True

@initrc.rc(depends_on=[load_settings])
async def ssl_cert(current_app):
    """
    Generate SSL Dev certificate
    
    Adapted from werkzeug.
    """
    logger.info("Checking SSL for certificate")

    cert_file = current_app.settings.CERT_CRT_FILE
    pkey_file = current_app.settings.CERT_KEY_FILE

    if cert_file and pkey_file:
        if cert_file.exists() ^ pkey_file.exists():
            raise RuntimeError("Certificate and key must be both present or both missing")

        if not cert_file.is_file() or not pkey_file.is_file():
            raise RuntimeError("Certificate and key must be files")

        raise Skipped("Certificate files exists")

    # Generate a new temporary certificate
    import tempfile
    import atexit

    pkey_handle, pkey_file = tempfile.mkstemp()
    cert_handle, cert_file = tempfile.mkstemp()
    atexit.register(os.remove, pkey_file)
    atexit.register(os.remove, cert_file)
    
    from thingi.mgmt.certgen import generate_cert

    fd_key = os.fdopen(pkey_handle, "wb")
    fd_cert = os.fdopen(cert_handle, "wb")
    hostname = current_app.settings.HOSTNAME
    
    generate_cert(fd_key, fd_cert, hostname)
    
    fd_key.close()
    fd_cert.close()
    
    current_app.settings.CERT_KEY_FILE = Path(pkey_file)
    current_app.settings.CERT_CRT_FILE = Path(cert_file)

    logger.debug("Generated temporary certificate %r and %r", pkey_file, cert_file)
    return True


@initrc.rc(depends_on=[load_settings])
async def start_mdns(current_app):
    """Start mDNS (zeroconf) service"""
    from thingi.discover import Discover

    if getattr(current_app, "zeroconf", None):
        logger.info("Restarting zeroconf")
        current_app.zeroconf.close()
        return True

    current_app.discover = Discover()

    return True


async def testing_hokey():
    """Hokey Pokey"""

    for i in range(3):
        await asyncio.sleep(1)
        logger.debug("Sleeping %d", i)

    return True

async def testing_skips():
    """Always skips"""

    for i in range(randint(1, 3)):
        await asyncio.sleep(1)

    raise Skipped("This is always skipped")

    return True

async def _main():
    """
    Function to test the initrc module.
    """
    from rich.live import Live
    from rich.layout import Layout
    from rich.console import Group
    from rich.console import Console
    console = Console()

    fps = 12.5

    from .app import MgmtApp
    app = MgmtApp()

    initrc.app = app

    initrc.rc(testing_hokey)
    initrc.rc(testing_skips)

    # For testing purposes, register this as decorator would

    task = asyncio.create_task(initrc.run())

    console.print("[bold]Initrc testing grounds[/bold]")
    spinners = [] * len(initrc.units)
    spinners = [console.status(f"Initrc {i.description}...", refresh_per_second=fps) for i in initrc.units.values()]


    layout = Group(
        *spinners
    )

    with Live(layout, refresh_per_second=fps, console=console) as live:
        while True:
            await asyncio.sleep(1 / live.refresh_per_second)
            for i, (k, s) in enumerate(initrc.status.items()):
                unit = initrc.units[k]
                match s:
                    case Status.PENDING:
                        spinners[i].update(f"[dim]{unit.description} [ PENDING ][/dim]")
                    case Status.RUNNING:
                        spinners[i].update(f"[bold]{unit.description}...[/bold]")
                    case Status.SKIPPED:
                        spinners[i].update(f"[bold yellow]{unit.description} [ SKIPPED ][/bold yellow]")
                        spinners[i].stop()
                    case Status.FAILED:
                        spinners[i].update(f"[bold red]{unit.description} [ FAILED ][/bold red]")
                        spinners[i].stop()
                    case Status.SUCCESS:
                        spinners[i].update(f"[bold green]{unit.description} [ DONE ][/bold green]")
                        spinners[i].stop()
            if task.done():
                break

    return True

if __name__ == "__main__":
    # This is for testing purposes

    from rich.logging import RichHandler
    logging.basicConfig(level=logging.DEBUG, handlers=[
        RichHandler()
    ])

    asyncio.run(_main())

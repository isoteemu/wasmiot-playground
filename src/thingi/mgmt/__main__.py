import logging
from textual.logging import TextualHandler
from .cli import cli
from .certgen import certgen
from .app import MgmtApp

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    
    logging.basicConfig(
        handlers=[TextualHandler()],
    )

    cli()

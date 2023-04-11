"""
Management console boot sequence

Decorator :func:`init` is used to register a function to be run during the boot sequence.
Decorated function must be a coroutine.

Decorated functions can depend on other functions by specifying the name of the function
as a string or by callback.

Example:

.. code-block:: python

    @init(depends_on=["init2"])
    async def init1():
        ...

    @init
    async def init2():
        ...

Boot sequence is run on parallel chunks, depending on the dependencies.
"""

# TODO: Make this all as a class

# Registry of bootstrap functions
import asyncio
from enum import Enum
from functools import partial, wraps
import logging
import os
from pathlib import Path
from random import randint
from typing import Callable, Dict, Iterable, NamedTuple, Set, Tuple, List, cast
from toposort import toposort

logger = logging.getLogger(__name__)

current_app = None

class Status(int, Enum):
    """
    Status of a init function.
    """
    SKIPPED = -1
    FAILED = 0b000   # -> 0
    SUCCESS = 0b001  # -> 1
    RUNNING = 0b010  # -> 2
    PENDING = 0b100  # -> 4

class InitRC(NamedTuple):
    """
    Stucture for registering init functions.
    """
    description: str
    func: Callable
    depends_on: List[Callable]


INITRC_ACTIONS: List[InitRC] = []


class Skipped(asyncio.CancelledError):
    """
    Raised when a init function is skipped.
    """
    pass


def initrc(depends_on: List[Callable|str] = []):
    """
    Decorator for registering a new init functions.
    
    First line of docstring is used as description.
    """
    # Get function description from docstring
    
    def decorator_register(func) -> Callable:

        @wraps(func)
        def func_callback(*args, **kwargs):
            logger.debug("Running %s", func.__name__)
            return func(*args, **kwargs)

        desc = func.__name__
        if func.__doc__:
            desc, *_ = func.__doc__.strip().split("\n")

        for i, depends in enumerate(depends_on):
            if isinstance(depends, str):
                depends_on[i] = locals()[depends]

        # Add the decorated function to the list of init functions.
        # See :func:`solve_bootorder`
        INITRC_ACTIONS.append(InitRC(desc, func_callback, depends_on))  # type: ignore

        return func_callback

    return decorator_register

@initrc()
async def load_settings():
    """Loading Settings"""
    from thingi.settings import Settings

    from .app import current_app

    current_app.settings = Settings()

    return True

@initrc(depends_on=[load_settings])
async def ssl_cert():
    """Generate SSL Dev certificate"""
    logger.info("Checking SSL for certificate")

    cert_file = current_app.settings.CERT_CRT_FILE
    pkey_file = current_app.settings.CERT_KEY_FILE

    if cert_file and pkey_file:
        if cert_file.exists() ^ pkey_file.exists():
            raise RuntimeError("Certificate and key must be both present or both missing")

        if not cert_file.is_file() or not pkey_file.is_file():
            raise RuntimeError("Certificate and key must be files")

        return Status.SKIPPED

    # Generate a new temporary certificate
    import tempfile
    import atexit

    pkey_handle, pkey_file = tempfile.mkstemp()
    cert_handle, cert_file = tempfile.mkstemp()
    #atexit.register(os.remove, pkey_file)
    #atexit.register(os.remove, cert_file)
    
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

@initrc()
async def hokey():
    """Hokey Pokey"""

    for i in range(3):
        await asyncio.sleep(1)
        print(f"SSL: {i}")

    return True


@initrc()
async def skips():
    """Always skips"""

    for i in range(randint(1, 3)):
        await asyncio.sleep(1)

    raise Skipped("This is always skipped")

    return True


def solve_bootorder(actions: List[InitRC] = INITRC_ACTIONS) -> List[Set[int]]:
    """
    Returns the bootorder as a list of functions.
    
    Returns a set of indexes into the INITRC_ACTIONS list, sorted by dependency.

    Dependencies are resolved by function hash. This means that if a function is decorated
    it will be treated as a different function. It might cause problems if the decorated
    function is used as a dependency, and the undecorated function is used as a callback.
    """

    deps = {}

    # Create a map of function to index
    # It's based on the hash of the function, to differentiate between
    # different functions with the same name.
    map = {a.func: i for i, a in enumerate(actions)}
    for desc, func, depends_on in actions:
        idx = map[func]
        deps[idx] = set((map[d] for d in depends_on))

    return list(toposort(deps))


async def run_init(status: List = [], actions: List[InitRC] = INITRC_ACTIONS, current_app=None):
    """
    Run initrc functions
    
    :param status: Status of the init functions.
    """

    print(current_app)

    solution = solve_bootorder(actions)

    print("Bootorder:", solution)

    for block in solution:
        for idx in block:
            print("Running", actions[idx].description, status[idx])

        await run_actions(block, status, actions)

        #loop.run_until_complete(run_actions(block, status, actions))
        #asyncio.run(run_actions(block, status, actions))

        for idx in block:
            print("...", actions[idx].description, status[idx])


async def run_actions(block: Iterable[int], statuses: List[Status], actions: List[InitRC]):
    """
    Run a block of init functions.
    """

    # Run tasks in parallel, but wait for them to complete
    # If a task fails, cancels all other tasks

    for idx in block:
        async with asyncio.TaskGroup () as tg:
            func = actions[idx].func
            statuses[idx]
            statuses[idx] = Status.RUNNING

            task = tg.create_task(_run_func(func))
            
            # This is a bit more complicated than it needs to be, because
            # we don't want to wait all tasks to complete before we store
            # the status.
            task.add_done_callback(partial(_action_complete, statuses, idx))


async def _run_func(func):
    """
    Wrapper to handle execption in init functions.
    """

    try:
        return await func()
    except Exception as e:
        logger.exception("Failed to run init function", exc_info=e)
        return Status.FAILED

def _action_complete(statuses, idx, task: asyncio.Task):
    """
    Callback for when an action is complete.
    
    """
    f = task.get_name()
    result = Status.SUCCESS
    status = Status.PENDING
    try:
        result = task.result()

        if result == Status.FAILED.value:
            status = Status.FAILED
        elif result == Status.SKIPPED.value:
            print(f, "Marked as Skipped", Status.SKIPPED.value)
            status = Status.SKIPPED
        elif result == None:
            status = Status.SUCCESS
        elif result & Status.SUCCESS.value:
            status = Status.SUCCESS
        else:
            status = Status.FAILED.value

    except Skipped:
        print("Skipped")
        status = Status.SKIPPED
    except Exception as e:
        status = Status.FAILED
        logger.exception("Failed to run init function", exc_info=e)
    
    statuses[idx] = status

async def _main():

    from rich.live import Live
    from rich.layout import Layout
    from rich.console import Group
    from rich.console import Console
    console = Console()

    fps = 12.5

    statuses = [] * len(INITRC_ACTIONS)
    spinners = [] * len(statuses)

    task = asyncio.create_task(run_init(statuses))

    spinners = [console.status(f"Initrc {i.description}...", refresh_per_second=fps) for i in INITRC_ACTIONS]

    layout = Group(
        "[bold]Initrc[/bold]",
        *spinners
    )

    with Live(layout, refresh_per_second=fps, screen=True) as live:
        while True:
            await asyncio.sleep(1 / live.refresh_per_second)
            for i, s in enumerate(statuses):
                match s:
                    case Status.PENDING:
                        spinners[i].update(f"[dim]{INITRC_ACTIONS[i].description} [ PENDING ][/dim]")
                    case Status.RUNNING:
                        spinners[i].update(f"[bold]{INITRC_ACTIONS[i].description}...[/bold]")
                    case Status.SKIPPED:
                        spinners[i].update(f"[bold yellow]{INITRC_ACTIONS[i].description} [ SKIPPED ][/bold yellow]")
                        spinners[i].stop()
                    case Status.FAILED:
                        spinners[i].update(f"[bold red]{INITRC_ACTIONS[i].description} [ FAILED ][/bold red]")
                        spinners[i].stop()
                    case Status.SUCCESS:
                        spinners[i].update(f"[bold green]{INITRC_ACTIONS[i].description} [ DONE ][/bold green]")
                        spinners[i].stop()

    await task
    return True


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    # This is for testing purposes

    from .app import MgmtApp
    current_app = MgmtApp()

    asyncio.run(_main())

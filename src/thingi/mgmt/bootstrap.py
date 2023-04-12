"""
Management console boot sequence

Decorator :func:`init` is used to register a function to be run during the boot sequence.
Decorated function must be a coroutine.

Decorated functions can depend on other functions by specifying the name of the function
as a string or by callback.

Example:

.. code-block:: python

    init = Init()

    @init.rc(depends_on=["init2"])
    async def init1():
        ...

    @init.rc
    async def init2():
        ...

Boot sequence is run on parallel chunks, depending on the dependencies.
"""

# TODO: Make this all as a class

# Registry of bootstrap functions
import asyncio
from enum import Enum
from functools import partial, wraps
from itertools import chain
import logging
import os
from pathlib import Path
from random import randint
from typing import Callable, Dict, Hashable, Iterable, NamedTuple, Set, Tuple, List
from toposort import toposort

logger = logging.getLogger(__name__)


class Status(int, Enum):
    """
    Status of a init function.
    """
    SUCCESS = 0b00001  # -> 1
    RUNNING = 0b00010  # -> 2
    PENDING = 0b00100  # -> 4
    FAILED  = 0b01000
    SKIPPED = 0b10000

class InitRC(NamedTuple):
    """
    Stucture for registering init functions.
    """
    description: str
    func: Callable
    depends_on: List[Callable]



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


async def load_settings():
    """Loading Settings"""
    from thingi.settings import Settings

    current_app.settings = Settings()

    return True


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


async def hokey():
    """Hokey Pokey"""

    for i in range(3):
        await asyncio.sleep(1)
        logger.debug("Sleeping %d", i)

    return True


async def skips():
    """Always skips"""

    for i in range(randint(1, 3)):
        await asyncio.sleep(1)

    raise Skipped("This is always skipped")

    return True


async def run_init(status: List = [], actions: List[InitRC] = [], current_app=None):
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


class Init():

    units: Dict[Hashable, InitRC]
    "List of init functions"
    status: Dict[Hashable, Status]
    "Status of init functions"

    def __init__(self, current_app=None):
        self.units = {}
        self.status = {}

        if current_app:
            self.app = current_app


    def rc(self, depends_on: List[Callable] = []):
        """
        Register a new function as init unit.
        
        Example::
        
        
        :param depends_on: List of functions that must be run before this function.

        """
        
        def decorator_register(func) -> Callable:

            @wraps(func)
            def func_callback(*args, **kwargs):
                logger.debug("Running %s", func.__name__)
                return func(*args, **kwargs)

            # Get function description from docstring
            desc = func.__name__
            if func.__doc__:
                desc, *_ = func.__doc__.strip().split("\n")

            # Check for string for callbacks to bind them functions in current closure.
            for i, depends in enumerate(depends_on):
                if isinstance(depends, str):
                    depends_on[i] = locals()[depends]

            # Add the decorated function to the list of init functions.
            # See :func:`solve_bootorder`
            self.units[func] = InitRC(desc, func_callback, depends_on)

            return func_callback

        return decorator_register


    def solution(self) -> Iterable[Iterable[Hashable]]:
        """
        Returns the bootorder as a list of sets of functions.

        Dependencies are resolved by function id. This means that if a function is decorated
        it will be treated as a different function. It might cause problems if the decorated
        function is used as a dependency, and the undecorated function is used as a callback.
        """

        # Most of this functions is just to convert the functions to primitive types
        # for the toposort algorithm.
        map = {f: id(f) for f in self.units.keys()}
        reverse_map = {v: k for k, v in map.items()}

        print("MAP", map)

        deps = {}
        for key, initrc in self.units.items():
            print("F", key, initrc.depends_on)
            idx = map[key]
            deps[idx] = set((map[d] for d in initrc.depends_on))

        solution = toposort(deps)

        # Now convert the solution back to functions
        solution = [[reverse_map[idx] for idx in block] for block in solution]

        return solution


    async def run(self):
        """
        Run initrc functions
        
        :param status: Status of the init functions.
        """

        solution = self.solution()

        # Status of functions that will cause a init function to be skipped
        failure_status = Status.FAILED + Status.SKIPPED

        # Reset status of all functions
        self.status = {f: Status.PENDING for f in chain.from_iterable(solution)}

        for block in solution:
            async with asyncio.TaskGroup () as tg:
                for idx in block:
                    unit = self.units[idx]
                    func = unit.func

                    # Check if any depends_on function has failed
                    failed = (f for f, s in self.status.items() if s & failure_status)
                    if set(unit.depends_on) & set(failed):
                        logger.debug("Skipping %r (%r) because of failed dependency", unit.description, func.__name__)
                        self.status[idx] = Status.SKIPPED
                        continue

                    self.status[idx] = Status.RUNNING
                    task = tg.create_task(_run_func(func))

                    # This is a bit more complicated than it needs to be, because
                    # we don't want to wait all tasks to complete before we store
                    # the status.
                    task.add_done_callback(partial(self._action_complete, idx))


    async def _run_func(self, func: Callable):
        """
        Wrapper to handle execption in init functions.
        """

        try:
            current_app = self.app
            return await func()
        except Exception as e:
            logger.exception("Failed to run init function", exc_info=e)
            return Status.FAILED

    def _action_complete(self, idx: Hashable, task: asyncio.Task):
        """
        Callback for when an action is complete.
        
        Sets the status of the action to the result of the task.
        """

        result = Status.SUCCESS
        status = Status.PENDING
        try:
            result = task.result()

            # Check result for different types of success and failure
            if result in [True, Status.SUCCESS, None] or result & Status.SUCCESS.value:
                status = Status.SUCCESS
            elif result in [False, Status.FAILED] or result & Status.FAILED.value:
                status = Status.FAILED
            elif result == Status.SKIPPED or result & Status.SKIPPED.value:
                status = Status.SKIPPED
            else:
                logger.warning("Unknown result from init function: %r", result)
                status = Status.FAILED

        except Skipped:
            status = Status.SKIPPED
        except Exception as e:
            status = Status.FAILED
            logger.exception("Failed to run init function", exc_info=e)

        self.status[idx] = status



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
    init = Init(app)

    init.rc()(load_settings)
    init.rc(depends_on=[load_settings])(ssl_cert)
    init.rc()(hokey)
    init.rc()(skips)

    spinners = [] * len(init.units)

    task = asyncio.create_task(init.run())
    
    await task

    spinners = [console.status(f"Initrc {i.description}...", refresh_per_second=fps) for i in init.units.values()]

    layout = Group(
        "[bold]Initrc[/bold]",
        *spinners
    )

    with Live(layout, refresh_per_second=fps, screen=True) as live:
        while True:
            await asyncio.sleep(1 / live.refresh_per_second)
            for i, (k, s) in enumerate(init.status.items()):
                unit = init.units[k]
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

    await task
    return True

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    # This is for testing purposes

    from .app import MgmtApp
    current_app = MgmtApp()

    asyncio.run(_main())

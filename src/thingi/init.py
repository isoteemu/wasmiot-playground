"""
Initialisation class

Decorator :func:`rc` is used to register a function to be run during the boot sequence.
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
        
    async def init3():
        ...
    
    init.rc(init3)

If init function requires access to current app, they can use the :arg:`current_app`
to request it:

.. code-block:: python

    def init_app(current_app):
        current_app.settings['key'] = "new value"
        ...

Boot sequence is run on parallel chunks, depending on the dependencies.
"""

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
from inspect import signature

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


    def rc(self, func: Callable | None = None, depends_on: List[Callable] = []):
        """
        Decorator to register a function as an init function.

        :param depends_on: List of functions that must be run before this function.
        """

        def decorator_register(func) -> Callable:

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
            self.units[func] = InitRC(desc, func, depends_on)

            return func

        if func:
            return decorator_register(func)
        
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

        deps = {}
        for key, initrc in self.units.items():
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
                    task = tg.create_task(self._run_func(func))

                    # This is a bit more complicated than it needs to be, because
                    # we don't want to wait all tasks to complete before we store
                    # the status.
                    task.add_done_callback(partial(self._action_complete, idx))


    async def _run_func(self, func: Callable):
        """
        Wrapper to handle execption in init functions.
        """
        try:
            # Check the function signature if it requires app
            if "current_app" in signature(func).parameters:
                return await func(current_app=self.app)
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

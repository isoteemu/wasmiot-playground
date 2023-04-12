import asyncio
from functools import partial, wraps
import json
import logging
from random import randintthingi.mgmt
from time import sleep
from typing import Any, Callable, List, NamedTuple, Optional, Tuple, cast
import click
from textual.screen import Screen
from textual.reactive import reactive
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Placeholder, Static, ListView, ListItem, Label, Button, LoadingIndicator, TextLog
from textual.containers import Container, Vertical
from textual.binding import Binding
from textual.logging import TextualHandler
from zeroconf import ServiceInfo
from textual import work
from rich.status import Status
from rich.text import Text

from thingi.settings import Settings

logger = logging.getLogger(__name__)

class Device(ListItem):
    def compose(self) -> ComposeResult:
        yield Button("Farts")


class DeviceList(Container):
    """A list of discovered devices"""

    devices = reactive([])
    selected = reactive(None)

    def compose(self) -> ComposeResult:

        self.border_title = 'Devices'

        with ListView():
            for device in self.devices:
                yield Device(device.name)
            yield Device()
            yield Device()


class DevicesScreen(Screen):
    TITLE = """mDNS WebThing Discovery App"""

    BINDINGS = [
        ("F5", "action_scan", "Refresh"),
    ]

    def run(self, *args: Any, **kwargs: Any) -> None:
        self.log("Starting...")
        self.action_scan()

    def compose(self) -> ComposeResult:
        with Container():
            yield DeviceList()

    def action_scan(self):
        self.log("Refreshing...")


class StatusWidget(Static):
    def __init__(self, *args, **kwargs):
        self._status = Status(args[0], spinner="dots")
        self._task: asyncio.Task
        self._func: Optional[Callable] = kwargs.pop("func", None)

        super().__init__(*args, **kwargs)

    def on_show(self):
        if self._func:
            self._task = asyncio.create_task(self._func())

        self.update_render = self.set_interval(1 / 12.5, self.update_spinner)

    def update_spinner(self) -> None:
        if self._task.done():
            self._status.stop()
            msg = self._status.renderable.text
            self.update_render.stop()

            if (exc := self._task.exception()):
                logger.exception(exc)
                self._status.update(msg + Text(" [FAILED]", style="bold red"))
            else:                
                self._status.update(msg + Text(" [ DONE ]", style="bold green"))

        self.update(self._status._spinner)



class BootstrapScreen(Screen):

    TITLE = "WasmIoT Management Console Bootup"

    def compose(self) -> ComposeResult:
        
        self.widget = Vertical()

            #yield LoadingIndicator(id="boot-progress")
            # self.widget = LoadingIndicator()

            # with self.widget:
            #     for desc, func in self.bootmessages:
            #         self.log(f"Running {func.__name__}")
            #         yield Label(desc)

            # yield self.widget

        self.spinners = {}

        with self.widget:

            yield Label(Text("Starting...", style="bold"))
            for desc, func, _ in BOOTSTRAP_ACTIONS:
                print(f"Preparing {func.__name__}")
                spinner = StatusWidget(desc, id=f"init-func-{func.__name__}")
                spinner._func = func
                self.spinners[func.__name__] = spinner
                yield spinner

        yield self.widget



class MgmtApp(App):
    
    TITLE = """WasmIoT Management Console"""
    CSS_PATH = "mgmt.css"

    BINDINGS = [
        Binding("ctrl+c,ctrl+q", "app.quit", "Quit", show=True),
    ]

    SCREENS = {
        'bootstrap': BootstrapScreen(),
        'devices': DevicesScreen(),
    }

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        self.push_screen("bootstrap")


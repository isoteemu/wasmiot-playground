import asyncio
from contextvars import ContextVar
from functools import partial, wraps
import json
import logging
from random import randint
from time import sleep
from typing import Any, Callable, List, NamedTuple, Optional, Tuple, cast
import click
from textual.screen import Screen
from textual.reactive import reactive
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Placeholder, Static, ListView, ListItem, Label, Button, LoadingIndicator, TextLog
from textual.containers import Container, Vertical, VerticalScroll, Horizontal
from textual.binding import Binding
from textual.logging import TextualHandler
from zeroconf import ServiceInfo
from textual import work
from rich.status import Status
from rich.text import Text
from gettext import gettext as _

from thingi.settings import Settings
from .cli import cli
from .bootstrap import Status as InitRCStatus

from werkzeug.local import LocalProxy
    
logger = logging.getLogger(__name__)

_mgmt_app = ContextVar("MgmtApp")
current_app: "MgmtApp" = LocalProxy(_mgmt_app, "app")  # type: ignore[assignment]

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
                self._status.update(msg + Text(" [FAILED]", style="bold red"))  # type: ignore
            else:
                self._status.update(msg + Text(" [ DONE ]", style="bold green"))  # type: ignore

        self.update(self._status._spinner)


class InitrcWidget(Static):
    status = reactive(InitRCStatus.PENDING)

    message_styles = {
        InitRCStatus.PENDING: Text(" [PENDING]", style="bold yellow")
    }

    def __init__(self, renderable, *args, **kwargs):
        self._title = renderable
        self._status = Status(self._title, spinner="dots")
        self.prev_status = self.status

        return super().__init__(self._status, *args, **kwargs)

    def update_spinner(self) -> None:
        self.update(self._status._spinner)
        print("CHECK:", self._title, self.status)

    def on_show(self):
        self.update_render = self.set_interval(1 / 1, self.update_spinner)

    def watch_status(self):
        
        msg = Text(self._title)

        match self.status:
            case InitRCStatus.PENDING:
                self._status.update(spinner="dots11")
                self.classes = ["pending"]
            case InitRCStatus.RUNNING:
                self._status.update(spinner="dots")
                self.classes = ["running"]
            case InitRCStatus.FAILED:
                self._status.update(spinner="dots")
                self.classes = ["failed"]


class BootstrapScreen(Screen):

    TITLE = "WasmIoT Management Console Bootup"

    statuses = []

    def compose(self) -> ComposeResult:
        
        self.widget = VerticalScroll(id="initrc")
        self._spinners = {}


        from .bootstrap import INITRC_ACTIONS
        initrc = INITRC_ACTIONS

        self.statuses = [reactive(-1)] * len(initrc)

        with self.widget: 

            for i, action in enumerate(initrc):
                message_widget = InitrcWidget(action.description) #, func=action.func)
                message_widget.status = self.statuses[i]

                yield message_widget

    def on_mount(self) -> None:
        from .bootstrap import run_init
        print("Running initrc")
        self.run_worker(run_init(self.statuses, current_app=self.app))
        
        self.update_render = self.set_interval(1, self.check_status)

    def check_status(self):
        print("check_status", self.statuses)


    def watch_statuses(self, statuses) -> None:
        print("watch_statuses", statuses)


class MgmtApp(App):
    
    TITLE = _("WasmIoT Management Console")

    CSS_PATH = "mgmt.css"

    BINDINGS = [
        Binding("ctrl+c,ctrl+q", "app.quit", _("Quit"), show=True),
    ]

    SCREENS = {
        'bootstrap': BootstrapScreen(),
        'devices': DevicesScreen(),
    }

    settings: Settings

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        self.push_screen("bootstrap")

    def run(self, *args, **kwargs):
        current_app = self
        return super().run(*args, **kwargs)


@cli.command()
#@click.option("--config", "-c", "config_file", type=click.Path(exists=True), default="config.json")
def main(config_file=None):

    app = MgmtApp()
    _mgmt_app.set(app)

    app.run()


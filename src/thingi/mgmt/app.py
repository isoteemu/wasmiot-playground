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
from thingi.init import Init

from thingi.settings import Settings
from .cli import cli
from .bootstrap import (
    Status as InitRCStatus
)

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

        super().__init__(self._status, *args, **kwargs)
    
        self.update_render = self.set_interval(1 / 12.5, self.update_spinner)

    def update_spinner(self) -> None:
        self.update(self._status)
        logger.debug("CHECK:", self._title, self.status)

    def watch_status(self):
        
        print("WATCH:", self._title, self.status)
        msg = Text(self._title)

        match self.status:
            case InitRCStatus.PENDING:
                msg += Text(" [PENDING]", style="")
                self._status.update(msg, spinner="dots")
                self.classes = ["pending"]
                self.update_render.stop()
            case InitRCStatus.RUNNING:
                msg += Text(" [RUNNING]", style="")
                self._status.update(msg, spinner="dots")
                self.update_render.start()
                self.classes = ["running"]
            case InitRCStatus.SKIPPED:
                msg += Text(" [SKIPPED]", style="bold")
                self._status.update(msg)
                self.classes = ["skipped"]
                self.update_render.stop()
            case InitRCStatus.FAILED:
                msg += Text(" [FAILED]", style="bold")
                self._status.update(msg)
                self.classes = ["failed"]
                self.update_render.stop()
            case InitRCStatus.SUCCESS:
                msg += Text(" [SUCCESS]", style="bold")
                self._status.update(msg)
                self.classes = ["success"]
                self.update_render.stop()
                

class BootstrapScreen(Screen):

    TITLE = "WasmIoT Management Console Bootup"
    initrc: Init

    def __init__(self, *args, **kwargs):
        from .bootstrap import initrc
        self.initrc = initrc

        super().__init__(*args, **kwargs)

    def compose(self) -> ComposeResult:
        
        self.widget = VerticalScroll(id="initrc")
        self._spinners = {}

        self.initrc.app = self.app
        units = self.initrc.units

        with self.widget: 

            for key, action in units.items():
                self._spinners[key] = InitrcWidget(action.description) #, func=action.func)
                self.initrc.status[key] = self._spinners[key].status

                yield self._spinners[key]

    def on_mount(self) -> None:
        print("Running initrc")
        self.run_worker(self.initrc.run)
        self.update_render = self.set_interval(1/12.5, self.check_status)

    def check_status(self):
        print("Widget:", self.widget)
        for key, widget in self._spinners.items():
            widget.status = self.initrc.status[key]
            print("Widget:", key, widget.status)
            #widget.watch_status()


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


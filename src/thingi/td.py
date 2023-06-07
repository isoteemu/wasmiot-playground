"""
Web of Things API and schema.

Currently makes two assumptions:
    - The default context is always `https://www.w3.org/2022/wot/td/v1.1#`
    - Wasmiot context is always `https://wetware.fi/2023/wasmiot/v0.1#` and
        is aliased as `wasmiot`.

..todo::
    - wasmiot module not really used. Currently relies only on wot module.

"""
from itertools import chain
import json
import uuid
from typing import Annotated, Any, Callable, Dict, Iterator, List, Optional, Set, Type, Union

from pydantic import BaseModel, Field
from pyld import jsonld

from .context import wasmiot, wot

from .utils import get_hostname

FORM_TEMPLATE = "/api/v1/{ns!s}/{name!s}"

class CompositeModel(wot.ThingDescription, wasmiot.ThingDescription):
    """
    Combines the Thing Description and the Wasmiot Description.
    """

    def __init__(self, **model):
        # Generate UUID and use it as fallback for name and ID.
        # NOTICE: This might not be unique, but helps with debugging.
        hostname = get_hostname()
        thing_uuid = uuid.uuid5(namespace=uuid.NAMESPACE_DNS, name=get_hostname())
        model.setdefault("title", f"Thing on {hostname!s}")

        model.setdefault("@id", f"urn:uuid:{thing_uuid!s}")
        model.setdefault("description", f"Automatically generated description for Thing on {hostname!s}")

        super().__init__(**model)

    def json(self, *, by_alias=True, exclude_unset: bool = True, **kwargs) -> str:
        """
        Generate a JSON representation of the Thing Description.
        """
        return super().json(by_alias=by_alias, exclude_unset=exclude_unset, **kwargs)


class Interaction(BaseModel):
    name: str
    url: str
    callback: Callable

    def __call__(self, *args: Any, **kwds: Any) -> Any:
        return self.callback(*args, **kwds)


class Thingi():

    td: wot.ThingDescription
    cls: Type[BaseModel] = CompositeModel

    interactions: List[Interaction] = Field(
        description="List of interactions.",
        default=[],
    )

    def __init__(self, td: wot.ThingDescription, **kwargs): 

        # TODO: Advertise properties, actions and events.
        self.td = td


    def generate_forms(self):
        """
        Generate forms from wasmiot entrypoints.
        """


    def invoke(self, name: str, *args: Any, **kwds: Any) -> Interaction:
        """
        Invoke an action.
        """
        match self.interactions:
            case Interaction(url=name):
                # TODO: Validate arguments.
                return self.interactions[name]
            case []: raise ValueError("No interactions defined.")


    def find_interactions(self, service: str) -> Iterator[Interaction]:
        """
        Return all the interactions by name or by url.

        Notice: Should return only one interaction.
        
        ..todo:: Maybe make a mapping of the interactions.
        """

        for interaction in self.interactions:
            if service in (interaction.url, interaction.name):
                yield interaction

    def find_interaction(self, service: str) -> Interaction:
        """
        Return an interaction by name or by url.
        """
        return next(self.find_interactions(service), None)


    @staticmethod
    def producer(doc: str | bytes, **kwargs) -> "Thingi":
        """
        Create a Thingi from a Thing Description.
        """

        # Add the default context by combining the two contexts.
        context = []
        from rich import print

        for base_class in __class__.cls.__bases__:
            context.extend(base_class().context_)

        description = jsonld_compact(doc, context)
        thing_desc = CompositeModel.parse_obj(description)

        return Thingi(description, **kwargs)


def jsonld_compact(doc: bytes | str | bytearray | Dict, default_context = []) -> Dict:
    """
    Compact a JSON-LD document.
    """

    data: Dict

    if not isinstance(doc, Dict):
        data = json.loads(doc)
    else:
        data = doc

    context = default_context

    compact = jsonld.compact(data, context, options={
        "activeCtx": True,
    })

    return compact

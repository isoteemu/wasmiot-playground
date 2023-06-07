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
from typing import Annotated, Any, Callable, Dict, List, Optional, Set, Type, Union

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


class Thingi():

    td: wot.ThingDescription
    cls: Type[BaseModel] = CompositeModel

    def __init__(self, td: wot.ThingDescription, **kwargs): 

        # TODO: Advertise properties, actions and events.
        self.td = td


    def set_property_handler(self, name: str, handler: callable):
        """
        Set a handler for a property.

        :param name: The name of the property.
        :param handler: The handler function.
        """
        ...


    @property
    def interactions(self) -> List[Dict]:
        """
        List of interactions.
        """
        return chain(self.td.properties, self.td.actions, self.td.events)

    @staticmethod
    def producer(doc: str | bytes, **kwargs) -> "Thingi":
        """
        Create a Thingi from a Thing Description.
        """
        if isinstance(doc, bytes):
            doc = doc.decode("utf-8")

        # Add the default context by combining the two contexts.
        context = []
        from rich import print

        for base_class in __class__.cls.__bases__:
            context.extend(base_class().context_)

        description = jsonld_compact(doc, context)
        td = CompositeModel.parse_obj(description)

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

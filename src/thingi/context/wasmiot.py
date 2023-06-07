"""
Wasmiot context models.

Adds own ontology to the Thing Description.

"""
from typing import Dict, List
from pydantic import BaseModel, Field


DEFALT_CONTEXT = "https://wetware.fi/2023/wasmiot/v0.1#"


class WasmiotBaseModel(BaseModel):
    pass


class ThingDescription(WasmiotBaseModel):
    context_: List[str | Dict[str, str]] = Field(alias="@context", default=[{"wasmiot": DEFALT_CONTEXT }])


class InteractionAffordance(WasmiotBaseModel):
    """
    Action Affordance with additional Wasmiot metadata.
    """

    depends_on: List[Dict] | None = Field(alias="wasmiot:dependsOn", default=None)
    """List of actions that must be executed before this action."""
    entrypoint: str | None = Field(alias="wasmiot:entrypoint", default=None)
    """ Action callback function. """

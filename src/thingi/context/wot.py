from datetime import datetime
from enum import Enum
from itertools import chain
from typing import Dict, Iterable, List, Set

from pydantic import BaseModel, Field

DEFAULT_CONTEXT = "https://www.w3.org/2022/wot/td/v1.1#"

class PropertyType(str, Enum):
    """
    Property types.
    """
    INTEGER = "integer"
    NUMBER = "number"


TYPE_MAPPINGS = {
    PropertyType.INTEGER: int,
    PropertyType.NUMBER: float,
}


class AnyURI(str):
    """A string that is a URI."""
    pass


class ThingBaseModel(BaseModel):
    class Config:
        extra = "allow"


class DataSchema(ThingBaseModel):
    title: str | None = None
    description: str | None = None
    type: PropertyType | None = None
    unit: str | None = None
    readOnly: bool = False
    writeOnly: bool = False


class AdditionalExpectedResponse(ThingBaseModel):
    """Communication metadata describing the expected response message for the
    additional response."""
    success: bool = False
    "Signals if an additional response should not be considered an error."
    contentType: str = "application/json"
    schema_: str | None = Field(alias="schema", default=None)


class ExpectedResponse(str):
    """Communication metadata describing the expected response message for the
    primary response."""
    pass


class Form(ThingBaseModel):
    href: AnyURI
    contentType: str = "application/json"

    response: ExpectedResponse | None = None
    additionalResponses: List[AdditionalExpectedResponse] = []


class InteractionAffordance(ThingBaseModel):
    title: str | None = None
    description: str | None = None
    forms: List[Form] = []


class PropertyAffordance(DataSchema, InteractionAffordance):
    observable: bool = False


class ActionAffordance(InteractionAffordance):
    pass


class EventAffordance(InteractionAffordance):
    data: DataSchema | None = None


class ThingDescription(ThingBaseModel):
    """
    Main class for the Thing Description.

    Thing Description (TD) is a machine-readable metadata format with
    standardized structure and semantics to describe Things.
    """
    context_: List[str | Dict[str,str]] = Field(
        alias="@context",
        default=[DEFAULT_CONTEXT]
    )
    """Context maps terms to URLs."""

    type_: str | Set[str] = Field(
        alias="@type",
        default=set(["Thing"])
    )

    id: str | None = Field(
        alias="@id",
        default=None
    )
    """Identifier of the Thing in form of a URI [RFC3986] (e.g., stable URI, 
    temporary and mutable URI, URI with local IP address, URN, etc.)."""

    title: str | None = None
    """human-readable title (e.g., display a text for UI representation) based
    on a default language."""

    description: str | None = None
    """Provides additional (human-readable) information based on a default
    language."""

    created: datetime | None = Field(default_factory=datetime.utcnow)
    modified: datetime | None = None

    # TODO: Add support for security.
    #securityDefinitions: Dict[str, Dict] = {}
    #security: str | List[str] | None = None

    properties: Dict[str, PropertyAffordance] | None = {}
    actions: Dict[str, ActionAffordance] | None = {}
    events: Dict[str, EventAffordance] | None = {}

    support: str | None = None
    """Provides information about the TD maintainer as URI scheme (e.g.,
    mailto [RFC6068], tel [RFC3966], https [RFC9112])."""
    links: List[str] | None = None
    """Web links to arbitrary resources that relate to the specified
    Thing Description."""

    @properties
    def interactions(self) -> Iterable[InteractionAffordance]:
        """
        Return all the interactions of the Thing.
        """
        return chain(
            self.properties.values(),
            self.actions.values(),
            self.events.values()
        )

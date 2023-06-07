# Deployment format

## Introduction

Formats can be categorized into two types: Orchestrator and Supervisor. The format consumed by orchestrator should be kept as simple as possible and familiar to the user. As the orchestrator has a wider understanding of the topology, it can generate a more complex format for the supervisor.

Format consumed by supervisor should contain all the necessary info for the device to work as standalone, and expose the webthing interface.

## Supervisor format requirements

 - _Needs to_ define dependencies between services
 - _Needs to_ provide a way to define or expand into the webthing interface
 - _Needs to_ define the entrypoint function
 - _Needs to_ provide a way to label the device features.

## WebThing Thing Description

Using the orchestrator to compose a [WebThing TD (Thing Description)](https://www.w3.org/TR/wot-thing-description11) is the most straightforward way to define the webthing interface. The orchestrator can generate the WebThing TD from the service definitions and the dependencies between them.

### Issues

1. __Volatility__: Format is very volatile, and can change between versions.
2. __Missing service linking__: Doesn't specify way to define dependencies between services.
3. __Missing entrypoint definition__: Doesn't specify a way to define the entrypoint function for the webthing interface.

### Solutions

The JSON-LD format used by WebThing TD contains the [schema field, referred as `@context`](https://www.w3.org/TR/json-ld11/#the-context), that defines the format used and it's version. This allows us to expand the format without breaking the existing implementations. We can create our own schema declaration, and use the WebThing TD format to expand format with the missing features.

```json
{
    "@context": [
        "https://www.w3.org/2022/wot/td/v1.1",
        {"wasmiot": "https://wetware.fi/2023/wasmiot/v1.0"}
    ],
    "@type": ["Thing", "wasmiot:Supervisor"],
    "title": "Some device",
    "properties": {
        "status": {
            "id": "urn:wasmiot:some_device_status",
            "type": "string",
            "forms": [],
            "wasmiot:entrypoint": "some_function_name",
            "wasmiot:dependsOn": [
                {
                    "id": "some_service_id",
                }
            ]
        }
    }
}
```

### Ontology

- `wasmiot:Supervisor`: Defines the device as a supervisor. This is used to identify wasmiot supervisor from other `Thing`s. To be able to identify as a supervisor and not a general thing, or composition of multiple things, both `Thing` and `wasmiot:Supervisor` types are required.

- `wasmiot:dependsOn`: Defines the dependencies between services. List of `key:value` pairs, that is used to find suitable services. Example:
    ```json
    "wasmiot:dependsOn": [
        {
            "id": "urn:specific_temperature_sensor",
            "type": "saref:Temperature sensor"
        }
    ]
    ```
    !!! note

        I might be using thease completely wrong here!

- `wasmiot:entrypoint`: Defines the entrypoint function for the webthing interface. Should be a string that contains the name of the function from the wasm module. Belongs to the [`InteractionAffordance`](https://www.w3.org/TR/wot-thing-description11/#interactionaffordance) class.

### Pydantic models

Creating the model from Thing Description is done with [pydantic](https://pydantic-docs.helpmanual.io/). Thing description json is loaded, and compacted using [pyld](https://pypi.org/project/PyLD/) to format the contexts. Resulting dictionary is then converted into pydantic models.

To handle multiple contexts there is some possibilities for creating the models:

- Create a model for every context, and use multi-inheritance to combine them. This would be the classical way of doing it, but it would require a lot of boilerplate code.
    ```python
    class WotProperty(BaseModel):
        ...

    class WasmiotProperty(BaseModel):
        ...

    class WotThing(BaseModel):
        property: WotProperty
    
    class WasmiotThing(BaseModel):
        property: WasmiotProperty

    class CompositeProperty(WotProperty, WasmiotProperty):
        ...

    class CompositeThing(WotThing, WasmiotThing):
        property: CompositeProperty
    ```

- Create model for every context, and use dynamic model creation to create composite models.

- TODO: maybe we can use [generics](https://docs.pydantic.dev/latest/usage/models/#generic-models) to create the models?

- `CombinedContext` proxy class?
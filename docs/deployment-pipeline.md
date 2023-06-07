
## Topology map

The topology map defines the state that the system should be - similar to the kubernetes deployment format. Kubernetes deployment format is too complicated and people hate it, so we need to make it simpler. It should be something aking
to the docker-compose file.

```yaml
services:
  manly_service:
    module: man[.wasm]
    entrypoint: mouth
    annotations:
      farts: smell
    environment:
      - HOME=cave
```

This file is then fed to the orchestrator, which will generate the deployment solution for the supervisor(s).

## Deployment solution

Orchestrator:
 - Takes the topology map as input
 - Has understanding of the supervisor(s) and their capabilities
 - Generates the deployment solution for the supervisor(s)
 - Links the services together
 - Pushes the deployment solution to the supervisor(s)



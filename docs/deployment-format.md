# Deployment format

Deployment format is package that contains all the information needed to deploy a service to a specific supervisor.

## Format

Using the Helm Charts as basis, the deployment format is a tarball[^maybe-tar] containing the following files:

```
urn:wasmiot:example_service:1.0.0/
├── 


[^maybe-tar]: The format is referred as tarball, but it could be a zip file or some other archive format.
# Teemus' Playground

## Configuration

Generate configuration file for management app
    $ python -m thingi.settings init

To view used configuration:
    $ python -m thingi.settings view

Configuration uses pydantic model for basis, and can be set with constraints. Currently it only writes json files, but plan is to expand it to use yaml for human editable files.

Configuration values can be overridden with configuration files (`~/.wasmiot.json`), with environment variables and with docker secrets.

## SSL Certificates

SSL certificates can be generated with:
    $ python -m thingi.mgmt certgen -k <private-key-file> -c <public-cert-file>

Manangement app also generates temporary certificates, that are removed after app exits.

## Management app

Start the management app:
    $ python -m thingi.mgmt

### Boot functions

Too fancy for what is needed. Boot functions can be registered with `initrc()`  decorator, and depencies can be declared with `initrc(depends_on=[func])`. Functions are run on blocks and on parallel, depending on their depenecies. It's actually currenlty slower that if it would run sequential. But it would not be as fun.
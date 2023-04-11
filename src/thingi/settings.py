"""
Settings for the Thingi service.

Settings are loaded from default config first, and populated with
environment variables. If a config file is specified, it will be loaded
and override the default config.

"""
import json
from pathlib import Path
import click
from pydantic import BaseSettings, Field, FilePath
from .utils import get_hostname

# Default config file locations
WELL_KNOWN_PATHS = [
    '/etc/wasmiot/wasmiot.json',
    '~/.wasmiot.json',
    'wasmiot.json'
]

default_config_path = Path("~/.wasmiot.json").expanduser()

def load_settings_json(base_settings: BaseSettings) -> dict:
    """
    Load settings from well-known paths.
    """
    settings = dict()
    for path in WELL_KNOWN_PATHS:
        path = Path(path)
        if path.exists():
            settings.update(json.load(path.open('r')))

    return settings

class Settings(BaseSettings):

    HOSTNAME: str = Field(
        title="Hostname",
        default=get_hostname(),
        description="Hostname of the current device."
    )

    CERT_KEY_FILE: FilePath | None = Field(
        title="Private key file",
        default=None,
        description="Path to the private key file for PKI authentication."
    )

    CERT_CRT_FILE: FilePath | None = Field(
        title="Public certificate file",
        default=None,
        description="Path to the public certificate file for PKI authentication."
    )

    class Config:
        # Store secrets in the default docker secrets directory
        secrets_dir = "/run/secrets"

        @classmethod
        def customise_sources(cls, init_settings, env_settings, file_secret_settings):
            """
            Additional settings sources.

            Reads settings from a :const:`WELL_KNOWN_PATHS` defined locations.
            """
            return (init_settings,
                    load_settings_json,  # <- Loads settings from well-known paths
                    env_settings,
                    file_secret_settings)

@click.group()
def cli():
    pass

@cli.command()
@click.argument('FILE', nargs=1,
                type=click.Path(file_okay=True, writable=True),
                default=default_config_path,
                required=True)
@click.option('--force', '-f', 'force', is_flag=True, default=False)
def init(file, force):
    """
    Create a new configuration file.
    
    :param file: Path to the configuration file.
    """
    settings = Settings()
    config_file = Path(file)

    if config_file.exists() and not force:
        click.confirm(f"Configuration file {config_file} already exists. Overwrite?", abort=True)

    with file.open('w') as f:
        f.write(settings.json())

    click.echo(f"Configuration file {config_file} created.")


@cli.command()
def view():
    """
    View the current configuration.
    """
    settings = Settings()
    click.echo(settings.json(indent=4))


if __name__ == "__main__":
    cli()

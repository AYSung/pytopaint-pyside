from dataclasses import dataclass
import yaml
from importlib import resources


@dataclass
class AppConfig:
    resolution: int


def import_config() -> AppConfig:
    file = resources.files('pytopaint.resources').joinpath('config.yml')
    with open(file) as stream:
        config = yaml.safe_load(stream)

    return AppConfig(**config)


appconfig = import_config()


# TODO: save_config

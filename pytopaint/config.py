from dataclasses import asdict, dataclass
from importlib import resources

import yaml


@dataclass
class AppConfig:
    resolution: int
    scaling_factor: int
    upper_arcsinh_limit: float
    lower_arcsinh_limit: float


def import_config() -> AppConfig:
    file = resources.files('pytopaint.resources').joinpath('config.yml')
    with open(file) as stream:
        config = yaml.safe_load(stream)

    return AppConfig(**config)


appconfig = import_config()


def save_config() -> None:
    file = resources.files('pytopaint.resources').joinpath('config.yml')
    with open(file, 'w') as handle:
        yaml.dump(
            asdict(appconfig),
            handle,
            default_flow_style=False,
            sort_keys=False,
            explicit_start=True,
        )

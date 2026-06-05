from dataclasses import asdict, dataclass

import yaml

from pytopaint.paths import config_file


@dataclass
class AppConfig:
    resolution: int
    scaling_factor: int
    upper_arcsinh_limit: float
    lower_arcsinh_limit: float


def import_config() -> AppConfig:
    with open(config_file) as stream:
        config = yaml.safe_load(stream)

    return AppConfig(**config)


appconfig = import_config()


def save_config() -> None:
    with open(config_file, 'w') as handle:
        yaml.safe_dump(
            asdict(appconfig),
            handle,
            default_flow_style=False,
            sort_keys=False,
            explicit_start=True,
        )

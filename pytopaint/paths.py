import shutil
from importlib import resources

from platformdirs import user_config_path

default_config_file = resources.files('pytopaint.resources').joinpath('config.yml')
default_layout_dir = resources.files('pytopaint.resources').joinpath('layouts/')

config_dir = user_config_path(appname='PytoPaint', ensure_exists=True)
config_file = config_dir / 'config.yml'

layout_dir = config_dir / 'layouts'
layout_dir.mkdir(parents=True, exist_ok=True)

if not config_file.exists():
    shutil.copy(src=default_config_file, dst=config_file)

if not any(layout_dir.iterdir()):
    shutil.copytree(src=default_layout_dir, dst=layout_dir, dirs_exist_ok=True)

import json
import yaml
import os
from utils.log import logger

config = {}


def load_config():
    global config

    config_yaml = "config.yaml"
    config_path = "config.json"

    if os.path.exists(config_yaml):
        with open(config_yaml, mode="r", encoding="utf-8") as fp:
            config = yaml.safe_load(fp)

    elif os.path.exists(config_path):
        config_str = read_file(config_path)
        config = json.loads(config_str)

    else:
        raise Exception("Config file is not exist, please create config.json according to config.template.json")

    logger.info(f"Load config: {config}")


def read_file(path):
    with open(path, mode="r", encoding="utf-8") as f:
        return f.read()


def conf():
    return config

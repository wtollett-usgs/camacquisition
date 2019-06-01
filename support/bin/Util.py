# -*- coding: utf-8 -*-

import json
import logging


def read_json_config(config_file):
    logger.debug(f'Reading config file: {config_file}')
    with open(config_file, 'r') as f:
        return json.load(f)


def setup_logging(name="Error logs"):
    global logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    fmt = "%(asctime)s %(levelname)s - %(message)s " \
          + "(%(filename)s:%(lineno)s PID %(process)d)"
    formatter = logging.Formatter(fmt)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    return logger

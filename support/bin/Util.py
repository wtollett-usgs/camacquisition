# -*- coding: utf-8 -*-

import logging


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

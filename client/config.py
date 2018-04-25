# -*- coding: utf-8-*-
import yaml
import logging
import os
from . import dingdangpath

_logger = logging.getLogger(__name__)
_config = {}


def init(config_name='profile.yml'):
    # Create config dir if it does not exist yet
    if not os.path.exists(dingdangpath.CONFIG_PATH):
        try:
            os.makedirs(dingdangpath.CONFIG_PATH)
        except OSError:
            _logger.error("Could not create config dir: '%s'",
                          dingdangpath.CONFIG_PATH, exc_info=True)
            raise

    # Check if config dir is writable
    if not os.access(dingdangpath.CONFIG_PATH, os.W_OK):
        _logger.critical("Config dir %s is not writable. Dingdang " +
                         "won't work correctly.",
                         dingdangpath.CONFIG_PATH)

    config_file = dingdangpath.config(config_name)
    global _config

    # Read config
    _logger.debug("Trying to read config file: '%s'", config_file)
    try:
        with open(config_file, "r") as f:
            _config = yaml.safe_load(f)
    except OSError:
        _logger.error("Can't open config file: '%s'", config_file)
        raise


def has(item):
    return item in _config


def get(item='', default=None):
    if not item:
        return _config
    try:
        return _config[item]
    except KeyError:
        _logger.warning("%s not specified in profile, defaulting to '%s'",
                        item, default)
        return default

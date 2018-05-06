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


def get_path(items, default=None):
    global _config
    curConfig = _config
    if isinstance(items, str) and items[0] == '/':
        items = items.split('/')[1:]
    for key in items:
        if key in curConfig:
            curConfig = curConfig[key]
        else:
            _logger.warning("/%s not specified in profile, defaulting to "
                            "'%s'", '/'.join(items), default)
            return default
    return curConfig


def has_path(items):
    global _config
    curConfig = _config
    if isinstance(items, str) and items[0] == '/':
        items = items.split('/')[1:]
    for key in items:
        if key in curConfig:
            curConfig = curConfig[key]
        else:
            return False
    return True


def has(item):
    return item in _config


def get(item='', default=None):
    if not item:
        return _config
    if item[0] == '/':
        return get_path(item, default)
    try:
        return _config[item]
    except KeyError:
        _logger.warning("%s not specified in profile, defaulting to '%s'",
                        item, default)
        return default

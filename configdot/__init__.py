import logging

from .configdot import (
    parse_config,
    ConfigContainer,
    ConfigItem,
    update_config,
    dump_config,
)

logging.getLogger('configdot').addHandler(logging.NullHandler())

import structlog
import logging.config
import yaml

from cryton_worker.etc import config
from cryton_worker.lib.util import constants

"""
Default Cryton logger setup and configuration
"""

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

try:
    with open(config.LOG_CONFIG, "rt") as f:
        config_file = yaml.safe_load(f.read())
except (AttributeError, FileNotFoundError):
    config_file = yaml.safe_load(constants.DEFAULT_LOG_CONFIG)
logging.config.dictConfig(config_file)

amqpstorm_logger = logging.getLogger("amqpstorm")

if config.DEBUG:
    logger = structlog.get_logger("cryton-worker-debug")
    logger.setLevel(logging.DEBUG)
    amqpstorm_logger.propagate = True
else:
    logger = structlog.get_logger("cryton-worker")
    logger.setLevel(logging.INFO)
    amqpstorm_logger.propagate = False

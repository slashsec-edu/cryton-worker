import structlog
import logging.config

from cryton_worker.etc import config

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

config_dict = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "%(message)s, [%(thread)d]"}
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "simple",
            "stream": "ext://sys.stdout"
        },
        "sys-logger": {
            "class": "logging.handlers.SysLogHandler",
            "level": "INFO",
            "address": "/dev/log",
            "formatter": "simple"
        },
    },
    "root": {
        "level": "NOTSET",
        "handlers": [],
        "propagate": True
    },
    "loggers": {
        "cryton-worker": {
            "level": "INFO",
            "handlers": ["sys-logger"],
            "propagate": False
        },
        "cryton-worker-debug": {
            "level": "DEBUG",
            "handlers": ["console"],
            "propagate": True
        }
    }
}

logging.config.dictConfig(config_dict)
amqpstorm_logger = logging.getLogger("amqpstorm")

logger = structlog.get_logger("cryton-worker-debug" if config.DEBUG else "cryton-worker")
logger.setLevel(logging.DEBUG if config.DEBUG else logging.INFO)
amqpstorm_logger.propagate = True if config.DEBUG else False

from datetime import datetime

# Main queue constants
ACTION = "action"
CORRELATION_ID = "correlation_id"
DATA = "data"
RESULT_PIPE = "result_pipe"
QUEUE_NAME = "queue_name"
PROPERTIES = "properties"
HIGH_PRIORITY = 0
MEDIUM_PRIORITY = 1
LOW_PRIORITY = 2

# Processor action types
ACTION_KILL_TASK = "_kill_task"
ACTION_FINISH_TASK = "_finish_task"
ACTION_START_TRIGGER = "_start_trigger"
ACTION_STOP_TRIGGER = "_stop_trigger"
ACTION_SEND_MESSAGE = "_send_message"
ACTION_SHUTDOWN_THREADED_PROCESSOR = "shutdown_threaded_processor"

# Event types
EVENT_VALIDATE_MODULE = "VALIDATE_MODULE"
EVENT_LIST_MODULES = "LIST_MODULES"
EVENT_LIST_SESSIONS = "LIST_SESSIONS"
EVENT_KILL_STEP_EXECUTION = "KILL_STEP_EXECUTION"
EVENT_HEALTH_CHECK = "HEALTH_CHECK"
EVENT_START_TRIGGER = "START_TRIGGER"
EVENT_STOP_TRIGGER = "STOP_TRIGGER"
EVENT_TRIGGER_STAGE = "TRIGGER_STAGE"

# Trigger types
HTTP = "HTTP"

# Trigger constants
T_HOST = "host"
T_PORT = "port"
T_TYPE = "trigger_type"
T_STAGE_EXECUTION_ID = "stage_execution_id"
T_REPLY_TO = "reply_to"
T_PARAMETERS = "parameters"

# Rabbit message constants
EVENT_T = "event_t"
EVENT_V = "event_v"
ATTACK_MODULE = "attack_module"
ATTACK_MODULE_ARGUMENTS = "attack_module_arguments"
DEFAULT_MSG_PROPERTIES = {"content_encoding": "utf-8", 'timestamp': datetime.now()}
TARGET_IP = "target_ip"
SESSION_LIST = "session_list"
MODULE_LIST = "module_list"

# Other constants
RETURN_CODE = "return_code"
STD_ERR = "std_err"
CODE_ERROR = -2
CODE_OK = 0
CODE_KILL = -3
FILE = "file"
FILE_CONTENT = "file_content"
FILE_ENCODING = "file_encoding"
BASE64 = "base64"
UTF8 = "utf8"

# Default log YAML config
DEFAULT_LOG_CONFIG = """
---
version: 1
disable_existing_loggers: False
formatters:
  simple:
    format: "%(message)s, [%(thread)d]"

handlers:
  console:
    class: logging.StreamHandler
    level: DEBUG
    formatter: simple
    stream: ext://sys.stdout

  sys-logger:
    class: logging.handlers.SysLogHandler
    level: INFO
    address: "/dev/log"
    formatter: simple

root:
  level: NOTSET
  handlers: []
  propagate: yes

loggers:
  cryton-worker:
    level: INFO
    handlers: [sys-logger]
    propagate: no

  cryton-worker-debug:
    level: DEBUG
    handlers: [console]
    propagate: yes
...
"""

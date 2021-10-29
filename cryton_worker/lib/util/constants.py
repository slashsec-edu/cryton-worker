from datetime import datetime
from schema import Optional, Or

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
ACTION_LIST_TRIGGERS = "_list_triggers"
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
EVENT_LIST_TRIGGERS = "LIST_TRIGGERS"

# Trigger types
HTTP = "HTTP"
MSF = "MSF"

# Trigger constants
TRIGGER_HOST = "host"
TRIGGER_PORT = "port"
TRIGGER_TYPE = "trigger_type"
TRIGGER_STAGE_EXECUTION_ID = "stage_execution_id"
TRIGGER_PARAMETERS = "parameters"
TRIGGER_ID = "trigger_id"
EXPLOIT = "exploit"
PAYLOAD = "payload"
EXPLOIT_ARGUMENTS = "exploit_arguments"
PAYLOAD_ARGUMENTS = "payload_arguments"


# RabbitMQ message keywords
EVENT_T = "event_t"
EVENT_V = "event_v"
ATTACK_MODULE = "attack_module"
ATTACK_MODULE_ARGUMENTS = "attack_module_arguments"
DEFAULT_MSG_PROPERTIES = {"content_encoding": "utf-8", "timestamp": datetime.now()}
TARGET_IP = "target_ip"
SESSION_LIST = "session_list"
MODULE_LIST = "module_list"
TRIGGER_LIST = "trigger_list"
ACK_QUEUE = "ack_queue"

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
REPLY_TO = "reply_to"

# ControlTask validation schemas
EVENT_VALIDATE_MODULE_SCHEMA = {ATTACK_MODULE: str, ATTACK_MODULE_ARGUMENTS: dict}
EVENT_LIST_MODULES_SCHEMA = dict
EVENT_LIST_SESSIONS_SCHEMA = {Optional(Or("type", "tunnel_local", "tunnel_peer", "via_exploit", "via_payload", "desc",
                                          "info", "workspace", "session_host", "session_port", "target_host", 
                                          "username", "uuid", "exploit_uuid", "routes", "arch")): Or(str, int)}
EVENT_KILL_STEP_EXECUTION_SCHEMA = {"correlation_id": str}
EVENT_HEALTH_CHECK_SCHEMA = {}
EVENT_START_TRIGGER_HTTP_SCHEMA = {"host": str, "port": int, "trigger_type": "HTTP", "reply_to": str, "routes": [
    {"path": str, "method": str, "parameters": [{"name": str, "value": str}]}]}
EVENT_START_TRIGGER_MSF_SCHEMA = {"host": str, "port": int, "exploit": str,
                                  Optional("exploit_arguments"): {Optional(str): Or(str, int)},
                                  "payload": str, Optional("payload_arguments"): {Optional(str): Or(str, int)},
                                  "trigger_type": "MSF", "reply_to": str}
EVENT_STOP_TRIGGER_SCHEMA = {"trigger_id": str}
EVENT_LIST_TRIGGERS_SCHEMA = {}

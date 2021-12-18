[[_TOC_]]

![Coverage](https://gitlab.ics.muni.cz/beast-public/cryton/cryton-worker/badges/master/coverage.svg)

# Cryton Worker

## Description
Cryton worker is an application for orchestrating and executing Cryton or custom attack modules (scripts) both locally 
and remotely. Cryton worker utilizes [RabbitMQ](https://www.rabbitmq.com/) as it's messaging protocol for asynchronous RPC.  
To control Cryton Worker, [Cryton Core](https://gitlab.ics.muni.cz/beast-public/cryton/cryton-core) is 
recommended. However, it is possible to use it as a standalone application and control it using [your own requests](#rabbit-api).

[Link to the documentation](https://beast-public.gitlab-pages.ics.muni.cz/cryton/cryton-documentation/).

## Installation
Important note: this guide only explains how to install **Cryton Worker** package. to be able to execute the 
attack scenarios, you also need to install the **[Cryton Core](https://gitlab.ics.muni.cz/beast-public/cryton/cryton-core)** 
package. If you want to use attack modules provided by Cryton, you also have to get 
**[Cryton Modules](https://gitlab.ics.muni.cz/beast-public/cryton/cryton-modules)**.

### Using virtual environment (recommended)

**Dependencies**
- Python >=3.8
- metasploit-framework
- pipenv (optional)

For manual installation all you need to do is **run the setup script** (it is recommended to use virtual environment, see the next step).
```
python3.8 setup.py install
```

It is recommended to **use virtual environment for installation**, for example using pipenv.
```
pipenv shell
python setup.py install
```

Everything should be set. Check if the installation was successful using:
```
cryton-worker
```

You should see a help page.

If there is an error due to missing *environment variables* go to the [settings section](#settings).

#### Development
For development, all you need to do is use `develop` instead of `install`.
```
pipenv shell
python setup.py develop
```

### Using Docker Compose

**NOTICE: This guide won't describe how to install or mount modules and applications used by them. 
Also, Triggers won't work, since the opened ports on Docker container can't be updated during uptime, 
you'll have to set them up before running the container.**

**Dependencies**
- docker.io
- docker-compose

First make sure you have installed dependencies:
```
sudo apt install docker.io docker-compose
``` 

Add yourself to the group *docker*, so you can work with Docker CLI without sudo:
```
sudo groupadd docker
sudo usermod -aG docker $USER
newgrp docker 
docker run hello-world
```

For correct installation you need to update `.env` file. For example `CRYTON_WORKER_RABBIT_RHOST` must contain 
the same address as your *RabbitMQ server* and `CRYTON_WORKER_RABBIT_WORKER_PREFIX` must be the same as the one used 
in *Cryton Core*. For more information about *Cryton Worker* settings go to the [settings section](#settings).


Now, run docker-compose, which will pull, build and start all necessary docker images:
```
cd cryton-worker/
docker-compose up -d
```

This process might take a while, especially if it is the first time you run it - Cryton-Worker image must be built.
After a while you should see something like this:
```
Creating cryton_worker ... done
```

Everything should be set. Check if the installation was successful using `docker-compose logs` and look for `[*] Waiting for messages.`.


## Settings
Cryton Worker uses environment variables for its settings. Please update variables for your use case.
```
CRYTON_WORKER_MODULES_DIR=CHANGE_ME
CRYTON_WORKER_DEBUG=False
CRYTON_WORKER_MSFRPCD_PASS=toor
CRYTON_WORKER_MSFRPCD_USERNAME=msf
CRYTON_WORKER_MSFRPCD_PORT=55553
CRYTON_WORKER_MSFRPCD_SSL=False
CRYTON_WORKER_RABBIT_USERNAME=admin
CRYTON_WORKER_RABBIT_PASSWORD=mypass
CRYTON_WORKER_RABBIT_RHOST=CHANGE_ME
CRYTON_WORKER_RABBIT_RPORT=5672
CRYTON_WORKER_RABBIT_WORKER_PREFIX=CHANGE_ME
CRYTON_WORKER_EMPIRE_RHOST=CHANGE_ME
CRYTON_WORKER_EMPIRE_RPORT=1337
CRYTON_WORKER_EMPIRE_USERNAME=empireadmin
CRYTON_WORKER_EMPIRE_PASSWORD=password123
CRYTON_WORKER_CONSUMER_COUNT=3
CRYTON_WORKER_PROCESSOR_COUNT=3
CRYTON_WORKER_MAX_RETRIES=3
CRYTON_WORKER_INSTALL_REQUIREMENTS=False
```

If you're using *pipenv* as your Python virtual environment, re-entering it should be enough to load variables from *.env* file.  
To update environment variable you can use *export* command. For example: `export CRYTON_WORKER_RABBIT_WORKER_PREFIX=my_worker`.
Some environment variables can be overridden in CLI. Try using `cryton-worker start --help`.

Settings description: 
- `CRYTON_WORKER_MODULES_DIR` - (**string**) Path to directory containing modules
- `CRYTON_WORKER_DEBUG` - (**boolean - True/False**) Run Worker in debug mode
- `CRYTON_WORKER_MSFRPCD_PASS` - (**string**) Password used for connection to Metasploit framework
- `CRYTON_WORKER_MSFRPCD_USERNAME` - (**string**) Username used for connection to Metasploit framework
- `CRYTON_WORKER_MSFRPCD_PORT` - (**int**) Port used for connection to Metasploit framework
- `CRYTON_WORKER_MSFRPCD_SSL` - (**boolean - True/False**) Use SSL to connect to Metasploit framework
- `CRYTON_WORKER_RABBIT_USERNAME` - (**string**) RabbitMQ's username used for connection
- `CRYTON_WORKER_RABBIT_PASSWORD` - (**string**) RabbitMQ's password used for connection
- `CRYTON_WORKER_RABBIT_RHOST` - (**string**) RabbitMQ's address used for connection
- `CRYTON_WORKER_RABBIT_RPORT` - (**int**) RabbitMQ's port used for connection
- `CRYTON_WORKER_RABBIT_WORKER_PREFIX` - (**string**) Prefix (name) used to identify Worker, must be unique for each Worker
- `CRYTON_WORKER_EMPIRE_RHOST` - (**string**) Empire's address used for connection
- `CRYTON_WORKER_EMPIRE_RPORT` - (**int**) Empire's port used for connection
- `CRYTON_WORKER_EMPIRE_USERNAME` - (**string**) Empire's username used for connection
- `CRYTON_WORKER_EMPIRE_PASSWORD` - (**string**) Empire's password used for connection
- `CRYTON_WORKER_CONSUMER_COUNT` - (**int**)  Consumers count to use for queues (higher == faster RabbitMQ requests consuming, but heavier processor usage)
- `CRYTON_WORKER_PROCESSOR_COUNT` - (**int**) Processors count to use for internal requests (higher == more responsive internal requests processing, but heavier processor usage)
- `CRYTON_WORKER_MAX_RETRIES` - (**int**) How many times to try to connect
- `CRYTON_WORKER_INSTALL_REQUIREMENTS` - (**boolean - True/False**) Install requirements.txt files in modules directories on start up

## Usage
To be able to use Worker, you need to update your `.env` file or export the variables. For example `CRYTON_WORKER_RABBIT_RHOST` must contain 
the same address as your *RabbitMQ server* and `CRYTON_WORKER_RABBIT_WORKER_PREFIX` must be the same as the one saved 
in *Cryton Core*. For more information about *Cryton Worker* settings go to the [settings section](#settings). Some 
environment variables can be overridden in CLI. Try using `cryton-worker start --help`.

To be able to **execute** (validate) **attack modules** you must download and save them into the same directory. Then update 
`CRYTON_WORKER_MODULES_DIR` environment variable to point to the correct location.  
Modules are hot swappable, meaning module doesn't have to be present at start up. This is especially useful for development.

Modules directory example:
```
tree CRYTON_WORKER_MODULES_DIR
CRYTON_WORKER_MODULES_DIR/
├── mod_hydra
│   └── mod.py
└── mod_cmd
    └── mod.py
```

To start Worker use `cryton-worker start` and you should see something like:
```
Starting..
To exit press CTRL+C
Connection does not exist. Retrying..
Connection to RabbitMQ server established.
[*] Waiting for messages.
```

If you see an error. Please check if variables are correct and try to start Worker again.

## Rabbit API
Worker is able to process any request sent through RabbitMQ to its Queues (`cryton_worker.PREFIX.attack.request`, 
`cryton_worker.PREFIX.control.request`, `cryton_worker.PREFIX.agent.request`)
defined using *PREFIX* (can be changed using CLI or environment variable).

Response is sent to queue defined using `reply_to` parameter in a *message.properties*.

### Attack requests
Requests to execute command or a module are being processed in `cryton_worker.PREFIX.attack.request` queue.  
List of supported requests:

#### Execute attack module
To execute an attack module, send a message to `cryton_worker.PREFIX.attack.request` queue in a format 
`{"ack_queue": "confirmation_queue", "step_type": "cryton/execute-on-worker", "attack_module": module_name, "attack_module_arguments": module_arguments}`

ACK response format
`{"return_code": 0, "correlation_id": "id"}`

Response format 
`{"return_code": 0, "std_err": "", "std_out": "", "mod_err": "", "mod_out": ""}`

#### Execute command on agent
To execute a command on a deployed agent, send a message to `cryton_worker.PREFIX.attack.request` queue in a format 
`{ "step_type": "empire/execute-on-agent", "arguments": { "shell_command": "whoami", "use_agent": "MyAgent" } }`

ACK response format
`{"return_code": 0, "correlation_id": "id"}`

Response format 
`{"return_code": 0, "std_err": "", "std_out": "", "mod_err": "", "mod_out": ""}`

#### Execute empire module on agent
To execute an empire module on a deployed agent, send a message to `cryton_worker.PREFIX.attack.request` queue in a format 
`{ "step_type": "empire/execute-on-agent", "arguments": { "empire_module": "python/collection/linux/pillage_user", "use_agent": "MyAgent" } }`

ACK response format
`{"return_code": 0, "correlation_id": "id"}`

Response format 
`{"return_code": 0, "std_err": "", "std_out": "", "mod_err": "", "mod_out": ""}`

### Agent requests
Requests to control empire agents are being processed in `cryton_worker.PREFIX.agent.request` queue.  
List of supported requests:

#### Deploy agent
Deploy an agent and send response containing the result.  
Example: `{ "step_type": "empire/deploy-agent", "arguments": { "stager_arguments": { "stager_type": "multi/bash", "agent_name": "MyAgent", "listener_name": "TestListener", "listener_port": 80 }, "session_id": "MSF_SESSION_ID" } }`

Response example: `{"return_code": 0, "std_out": "Agent 'MyAgent' deployed on target 192.168.33.12."}`

### Control requests
To perform a control event send a message to `cryton_worker.PREFIX.control.request` queue in a format 
`{"event_t": type, "event_v": value}`. Response format `{"event_t": type, "event_v": value}`.  
List of supported requests:

#### Validate module
Validate a module and send response containing the result.  
Example: `"{"event_t": "VALIDATE_MODULE", "event_v": {"attack_module": module_name, "attack_module_arguments": module_arguments}}"`

Response example: `"{"event_t": "VALIDATE_MODULE", "event_v": {"return_code": 0, "std_out": "output"}}"`

#### List modules
List available modules and send response containing the result.  
Example: `"{"event_t": "LIST_MODULES", "event_v": {}}"`

Response example: `"{"event_t": "LIST_MODULES", "event_v": {"module_list": ["module_name"]}}"`

#### List sesions
List available Metasploit sessions and send response containing the result.  
Example: `"{"event_t": "LIST_SESSIONS", "event_v": {"target_host": target_ip}}"`

Response example: `"{"event_t": "LIST_SESSIONS", "event_v": {"session_list": ["session_id"]}}"`

#### Kill Step execution
Kill running Step (module) and send response containing the result.  
Example: `"{"event_t": "KILL_STEP_EXECUTION", "event_v": {"correlation_id": correlation_id}}"`

Response example: `"{"event_t": "KILL_STEP_EXECUTION", "event_v": {"return_code": -2, "std_err": "exception"}}"`

#### Health check
Check if Worker is alive and send response containing the result.  
Example: `"{"event_t": "HEALTH_CHECK", "event_v": {}}"`

Response example: `"{"event_t": "HEALTH_CHECK", "event_v": {"return_code": 0}}"`

#### Start trigger
Start trigger and send response containing the result.  
Example for HTTPTrigger: 
  `"{"event_t": "START_TRIGGER", "event_v": {"host": host, "port": port, "trigger_type": "HTTP", "reply_to": reply_to_queue, 
  "routes": [{"path": path, "method": method, "parameters": [{"name": name, "value": value}]}]}}"`

Response example for HTTPTrigger: `"{"event_t": "START_TRIGGER", "event_v": {"return_code": 0, "trigger_id": "123"}}"`

#### Stop trigger
Stop trigger and send response containing the result.  
Example for HTTPTrigger: 
  `"{"event_t": "STOP_TRIGGER", "event_v": {"trigger_id": "123"}}"`

Response example for HTTPTrigger: `"{"event_t": "STOP_TRIGGER", "event_v": {"return_code": -2, "std_err": "exception"}}"`

#### List triggers
List available triggers and send response containing the result.  
Example: `"{"event_t": "LIST_TRIGGERS", "event_v": {}}"`

Response example: `"{"event_t": "LIST_TRIGGERS", "event_v": {"trigger_list": [{"id": "123", "trigger_param": "trigger_param_value", ...}]}}"`

#### Trigger Stage (Response only)
Sent when Trigger is activated.  
Response example: `"{"event_t": "TRIGGER_STAGE", "event_v": {"stage_execution_id": stage_execution_id}}"`

## Creating modules
To be able to execute a module (Python script), you have to follow few rules:
- Each module must have its own directory with its name.
- Name your script (module) `mod.py`.
- Your module must contain an `execute` function which takes *dict* argument and returns *dict* argument. It's an entry point for executing it.
- Your module should contain a `validate` function which takes *dict* argument, validates it and returns 0 if it's okay, else raises an exception.

Path example:  
`/CRYTON_WORKER_MODULES_DIR/my-module-name/mod.py`

Where:  
- **CRYTON_WORKER_MODULES_DIR** has to be the same path as is defined in *CRYTON_WORKER_MODULES_DIR* environmental variable.
- **my-module-name** is the directory containing your module.
- **mod.py** is your main module file.

Module (`mod.py`) simple example:  
```python
def validate(arguments: dict) -> int:
    if arguments != {}:
        return 0  # If arguments are valid.
    raise Exception("No arguments")  # If arguments aren't valid.

def execute(arguments: dict) -> dict:
    # Do stuff.
    return {"return_code": 0, "mod_out": ["x", "y"]}

```

### Input parameters
Every module has its own input parameters specified. These input parameters are given as a dictionary to the 
module `execute` (when executing the module) or `validate` (when validating the module parameters) function. 

### Output parameters
Every attack module returns a dictionary with following keys:

| Parameter name | Parameter meaning                                                                                                                                                                                                                                 |
|----------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `return_code`  | Numeric representation of result (0, -1, -2) <br />0 (OK) means the module finished successfully<br />-1 (FAIL) means the module finished unsuccessfully<br />-2 (EXCEPTION) means the module finished with an unhandled error                    |
| `mod_out`      | Parsed output of module. Eg. for bruteforce module, this might be a list of found usernames and passwords.                                                                                                                                        |
| `mod_err`      | Error message with description of the problem.                                                                                                                                                                                                    |
| `std_out`      | Standard output (`std_out`) of any executed command (but mostly None)                                                                                                                                                                             |
| `std_err`      | Standard error (`std_err`) of any executed command (but mostly None)                                                                                                                                                                              |
| `file`         | A module can also return a file. It has to be a Python dictionary with keys `file_name` and `file_content` (optionally `file_encoding`, which can contain only `"base64"` or `None`). The file will be stored on the machine running Cryton Core. |

### Prebuilt functionality
Worker provides prebuilt functionality to make building modules easier. Import it using:
```python
from cryton_worker.lib.util import module_util
```

It gives you access to:
#### Metasploit
Wrapper for *MsfRpcClient* from *[pymetasploit3](https://pypi.org/project/pymetasploit3/)*.
Examples:
```python
# Check if connection to msfrpcd is OK before doing anything.
from cryton_worker.lib.util.module_util import Metasploit
msf = Metasploit()
if msf.is_connected():
    msf.do_stuff()
```
```python
from cryton_worker.lib.util.module_util import Metasploit
search_criteria = {"via_exploit": "my/exploit"}
found_sessions = Metasploit().get_sessions(**search_criteria)
```
```python
from cryton_worker.lib.util.module_util import Metasploit
output = Metasploit().execute_in_session("my_command", "session_id")
```
```python
from cryton_worker.lib.util.module_util import Metasploit
options = {"exploit_arguments": {}, "payload_arguments": {}}
Metasploit().execute_exploit("my_exploit", "my_payload", **options)
```
```python
from cryton_worker.lib.util.module_util import Metasploit
token = Metasploit().client.add_perm_token()
```
```python
from cryton_worker.lib.util.module_util import Metasploit
output = Metasploit().get_parameter_from_session("session_id", "my_param")
```

#### get_file_binary
Function to get file as binary.  
Example:
```python
from cryton_worker.lib.util.module_util import get_file_binary
my_file_content = get_file_binary("/path/to/my/file")
```

#### File
Class used with *[schema](https://pypi.org/project/schema/)* for validation if file exists.  
Example:
```python
from schema import Schema
from cryton_worker.lib.util.module_util import File
schema = Schema(File(str))
schema.validate("/path/to/file")
```

#### Dir
Class used with *[schema](https://pypi.org/project/schema/)* for validation if directory exists.  
Example:
```python
from schema import Schema
from cryton_worker.lib.util.module_util import Dir
schema = Schema(Dir(str))
schema.validate("/path/to/directory")
```


### Module example
```python
from schema import Schema
from cryton_worker.lib.util.module_util import get_file_binary, File


def validate(arguments: dict) -> int:
    """
    Validate input arguments for the execute function.
    :param arguments: Arguments for module execution
    :raises: schema.SchemaError
    :return: 0 If arguments are valid
    """
    conf_schema = Schema({
        'path': File(str),
    })

    conf_schema.validate(arguments)
    return 0


def execute(arguments: dict) -> dict:
    """
    This attack module can read a local file.
    Detailed information should be in README.md.
    :param arguments: Arguments for module execution
    :return: Generally supported output parameters (for more information check Cryton Worker README.md)
    """
    # Set default return values.
    ret_vals = dict()
    ret_vals.update({'return_code': -1})
    ret_vals.update({'mod_out': None})
    ret_vals.update({'mod_err': None})

    # Parse arguments.
    path_to_file = arguments.get("path")

    try:  # Try to get file's content as binary.
        my_file = get_file_binary(path_to_file)
    except Exception as ex:  # In case of fatal error (expected) update mod_err.
        ret_vals.update({'mod_err': str(ex)})
        return ret_vals

    ret_vals.update({'return_code': 0})  # In case of success update return_code to '0' and send file to Cryton Core.
    ret_vals.update({'file': {"file_name": "my_file", "file_content": my_file}})
    return ret_vals

```

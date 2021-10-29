import importlib.util
import glob
import base64
import os
from types import ModuleType
from pymetasploit3.msfrpc import MsfRpcClient, ExploitModule, PayloadModule
import traceback
import subprocess
import sys
import time
from queue import PriorityQueue
from multiprocessing.managers import SyncManager
from dataclasses import dataclass, field

from cryton_worker.etc import config
from cryton_worker.lib.util import logger, constants as co


def run_module(module_path: str, arguments: dict) -> dict:
    """
    Execute module and optionally update its result (file).
    :param module_path: Path to the module directory relative to config.MODULES_DIR
    :param arguments: Arguments passed to execute function
    :return: Updated execution result
    """
    logger.logger.debug("Running module.", module_name=module_path, arguments=arguments)
    result = execute_module(module_path, arguments)

    # Encode file contents as base64.
    file = result.get(co.FILE)
    if file is not None and isinstance(file, dict):  # Check if file is dict and get contents and encoding.
        file_content = file.get(co.FILE_CONTENT, "")
        file_encoding = file.get(co.FILE_ENCODING, "")

        if not isinstance(file_content, bytes):  # If contents if not bytes, convert it.
            if not isinstance(file_content, str):
                file_content = str(file_content)
            file_content = bytes(file_content, co.UTF8)

        if file_encoding != co.BASE64:  # If not already encoded as base64, encode it.
            file_content = base64.b64encode(file_content)

        # Conversion back from bytes to string.
        file.update({co.FILE_CONTENT: file_content.decode(), co.FILE_ENCODING: co.BASE64})
        logger.logger.debug("Encoded file content.", module_name=module_path, arguments=arguments)

    logger.logger.debug("Module run finished.", module_name=module_path, arguments=arguments, ret=result)
    return result


def execute_module(module_path: str, arguments: dict) -> dict:
    """
    Execute module defined by path and arguments.
    :param module_path: Path to the module directory relative to config.MODULES_DIR
    :param arguments: Arguments passed to execute function
    :return: Execution result
    """
    logger.logger.debug("Executing module.", module_name=module_path, arguments=arguments)
    try:  # Try to import the module.
        module_obj = import_module(module_path)
    except Exception as ex:
        return {co.RETURN_CODE: -2, co.STD_ERR: f"Couldn't import module {module_path}. Original error: {ex}."}

    try:  # Check if it has execute function.
        executable = module_obj.execute
    except AttributeError:
        result = {co.RETURN_CODE: -2, co.STD_ERR: f"Module {module_path} does not have execute function"}
    else:
        try:  # Run the execute function.
            result = executable(arguments)
        except Exception as ex:
            result = {co.RETURN_CODE: -2, co.STD_ERR: str({"module": module_path, "ex_type": str(ex.__class__),
                                                           "error": ex.__str__(), "traceback": traceback.format_exc()})}

    logger.logger.debug("Module execution finished.", module_name=module_path, arguments=arguments, result=result)
    return result


def validate_module(module_path: str, arguments: dict) -> dict:
    """
    Validate module defined by path and arguments.
    :param module_path: Path to the module directory relative to config.MODULES_DIR
    :param arguments: Arguments passed to validate function
    :return: Validation result
    """
    logger.logger.debug("Validating module.", module_name=module_path, arguments=arguments)

    try:  # Try to import the module.
        module_obj = import_module(module_path)
    except Exception as ex:
        return {co.RETURN_CODE: -2, co.STD_ERR: f"Couldn't import module {module_path}. Original error: {ex}."}

    try:  # Check if it has validate function.
        executable = module_obj.validate
    except AttributeError:
        result = {co.RETURN_CODE: -2, co.STD_ERR: f"Module {module_path} does not have validate function."}
    else:
        try:  # Run the validate function.
            return_code = executable(arguments)
            result = {co.RETURN_CODE: return_code, "std_out": f"Module {module_path} is valid."}
        except Exception as ex:
            result = {co.RETURN_CODE: -2, co.STD_ERR: str({"module": module_path, "ex_type": str(ex.__class__),
                                                           "error": ex.__str__(), "traceback": traceback.format_exc()})}

    logger.logger.debug("Module validation finished.", module_name=module_path, arguments=arguments, result=result)
    return result


def import_module(module_path: str) -> ModuleType:
    """
    Import module defined by path. The module does not have to be installed,
    as the path is being added to the system PATH.
    :param module_path: Path to the module directory relative to config.MODULES_DIR
    :return: Imported module object
    """
    logger.logger.debug("Importing module.", module_name=module_path)
    module_name = "mod"
    module_path = os.path.join(config.MODULES_DIR, module_path, module_name + ".py")

    module_spec = importlib.util.spec_from_file_location(module_name, module_path)
    module_obj = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module_obj)
    return module_obj


class Metasploit:
    def __init__(self, username: str = config.MSFRPCD_USERNAME, password: str = config.MSFRPCD_PASS,
                 port: int = config.MSFRPCD_PORT, ssl: bool = config.MSFRPCD_SSL, **kwargs):
        """
        Wrapper class for MsfRpcClient.
        :param username: Username used for connection
        :param password: Password used for connection
        :param port: Port used for connection
        :param ssl: Use SSL for connection
        :param kwargs: Additional arguments passed to MsfRpcClient
        """
        try:
            self.client = MsfRpcClient(password=password, username=username, port=port, ssl=ssl, **kwargs)
        except Exception as ex:
            logger.logger.error(str(ex))
            self.error = ex
        else:
            self.error = None

    def is_connected(self):
        """
        Checks if there are anny errors from connection creation.
        :return: True if is connected to msfrpcd
        """
        if self.error is None:
            return True
        return False

    def get_sessions(self, **kwargs) -> list:
        """
        Get list of available sessions that meet search requirements.
        :param kwargs: Search requirements
            Possible search requirements with example values:
                'type': 'shell',
                'tunnel_local': '192.168.56.10:555',
                'tunnel_peer': '192.168.56.1:48584',
                'via_exploit': 'exploit/multi/handler',
                'via_payload': 'payload/python/shell_reverse_tcp',
                'desc': 'Command shell',
                'info': '',
                'workspace': 'false',
                'session_host': '192.168.56.1',
                'session_port': 48584,
                'target_host': '',
                'username': 'vagrant',
                'uuid': 'o3mnfksh',
                'exploit_uuid': 'vkzl8sib',
                'routes': '',
                'arch': 'python'
        :return: Matched sessions
        """
        logger.logger.debug("Listing sessions.", kwargs=kwargs)

        found_sessions = []
        for session_id, session_details in self.client.sessions.list.items():
            add_session = True
            for key, val in kwargs.items():
                detail = session_details.get(key)
                if detail != val and val not in detail:
                    add_session = False
                    break

            if not add_session:
                continue
            found_sessions.append(session_id)

        logger.logger.debug("Finished listing sessions.", found_sessions=found_sessions)
        return found_sessions

    def execute_in_session(self, command: str, session_id: str, end_check: str = None, close: bool = False) -> str:
        """
        Execute command in MSF session. Optionally close it.
        :param command: Command to execute
        :param session_id: Metasploit session ID
        :param end_check: Letters that when found will end output gathering from exploit execution
        :param close: If the session should be closed after executing the command
        :raises:
            KeyError if session cannot be read
        :return: Output from the shell
        """
        shell = self.client.sessions.session(session_id)
        if end_check is None:
            shell.write(command)
            result = shell.read()
        else:
            result = shell.run_with_output(command, end_check)

        if close:
            shell.stop()
        return result

    def execute_exploit(self, exploit: str, payload: str = None, **kwargs) -> None:
        """
        Execute exploit in MSF. Optionally with payload.
        :param exploit: Exploit name (same as in MSF)
        :param payload: Payload name (same as in MSF)
        :param kwargs: Additional arguments for exploit and payload
            exploit_arguments: dict
            payload_arguments: dict
        :return: None
        """
        exploit_module: ExploitModule = self.client.modules.use(co.EXPLOIT, exploit)
        exploit_module.update(kwargs.get(co.EXPLOIT_ARGUMENTS, {}))

        payload_module: PayloadModule = self.client.modules.use(co.PAYLOAD, payload)
        if payload is not None:
            payload_module.update(kwargs.get(co.PAYLOAD_ARGUMENTS, {}))

        exploit_module.execute(payload=payload_module)


def list_modules() -> list:
    """
    Get a list of available modules.
    :return: Available modules
    """
    logger.logger.debug("Listing modules.")
    default_modules_dir = config.MODULES_DIR
    # List all python files, exclude init files
    files = [f.replace(default_modules_dir, "") for f in glob.glob(default_modules_dir + "**/*.py", recursive=True)]
    files = list(filter(lambda a: a.find("__init__.py") == -1, files))

    logger.logger.debug("Finished listing modules.", modules_list=files)
    return files


def install_modules_requirements(verbose: bool = False) -> None:
    """
    Go through module directories and install all requirement files.
    :param verbose: Display output from installation
    :return: None
    """
    additional_args = {}
    if not verbose:
        additional_args.update({"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL})

    logger.logger.debug("Installing module requirements.")
    for root, dirs, files in os.walk(config.MODULES_DIR):
        for filename in files:
            if filename == "requirements.txt":
                subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", os.path.join(root, filename)],
                                      **additional_args)


@dataclass(order=True)
class PrioritizedItem:
    """
    Item used for ManagerPriorityQueue.
    Priority parameter decides which item (PrioritizedItem) will be processed first.
    Timestamp parameter makes sure the order of processed items (PrioritizedItems) is preserved (AKA FIFO).
    Item parameter stores the process defining value.
    """
    priority: int
    item: dict = field(compare=False)
    timestamp: int = time.time_ns()


class ManagerPriorityQueue(PriorityQueue):
    """
    Wrapper class for PriorityQueue.
    If PriorityQueue is used in multiprocessing.managers.*Manager its parameters can't be used,
    therefore the get_attribute method. For example instead of "ManagerPriorityQueue.queue"
    use ManagerPriorityQueue.get_attribute("queue").
    """
    def get_attribute(self, name):
        return getattr(self, name)


class WrapperManager(SyncManager):
    """
    Wrapper class for SyncManager.
    """


def get_manager() -> WrapperManager:
    """
    Get WrapperManager, register ManagerPriorityQueue and start it.
    :return: Manager object with registered ManagerPriorityQueue as PriorityQueue
    """
    WrapperManager.register("PriorityQueue", ManagerPriorityQueue)
    manager = WrapperManager()
    manager.start()
    return manager

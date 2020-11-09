import importlib
from cryton_worker.lib import logger
import sys
import glob
import base64
import os
from schema import Schema
from pymetasploit3.msfrpc import MsfRpcClient

from cryton_worker.etc import config


def execute_module(name: str, arguments: dict) -> dict:
    """
    Execute specified module by name with arguments.
    :param name: name of the module relative to config.MODULES_DIR
    :param arguments: additional module arguments
    :return: execution result
    """
    logger.logger.info("Executing module", module_name=name, arguments=arguments)

    ret = run_executable(name, arguments)

    # Encode file contents as base64
    ret_file = ret.get('file')
    if isinstance(ret_file, dict):
        file_contents = ret_file.get('file_contents')
        if not isinstance(file_contents, (bytes, str)):
            file_contents = bytes(str(file_contents), 'utf8')
        if isinstance(file_contents, str):
            file_contents = bytes(file_contents, 'utf8')
        if isinstance(file_contents, bytes):
            # If already encoded
            if ret_file.get('file_contents_encoding') == 'base64':
                file_contents_b64 = file_contents
            else:
                file_contents_b64 = base64.b64encode(file_contents)

            # conversion back from bytes to string
            ret_file.update({'file_contents': file_contents_b64.decode(), 'file_contents_encoding': 'base64'})
        # TODO: file content must be saved somewhere or else it will brake the execution, or at least send an err msg
        else:
            raise TypeError('Cannot parse type "{}" of data in "file"'.format(type(file_contents)))

    logger.logger.info("Module execution finished", module_name=name, arguments=arguments, ret=ret)
    return ret


def run_executable(module_path: str, executable_args: dict) -> dict:
    """
    Run module specified by name and arguments. The module does not have to be installed,
    as the path is being added to the system PATH.
    :param module_path: path to the module directory relative to config.MODULES_DIR
    :param executable_args: additional module arguments
    :return: execution result
    """
    try:
        module_obj = import_module(module_path)
    except Exception as ex:
        return {'return_code': -2, 'std_err': 'Either module {} does not exist or there is some other problem. '
                                              'Original error: {}.'.format(module_path, ex)}

    try:
        executable = module_obj.execute
    except AttributeError:
        ret = {'return_code': -2, 'std_err': 'Module {} does not have execute function'.format(module_path)}
    else:
        try:
            ret = executable(executable_args)
        except Exception as ex:
            ret = {'return_code': -1, 'std_err': str(ex)}

    return ret


def validate_module(name: str, arguments: dict) -> dict:
    """
    Validate specified module by name with arguments.
    :param name: name of the module relative to config.MODULES_DIR
    :param arguments: additional module arguments
    :return: validation result
    """
    logger.logger.info("Validating module", module_name=name, arguments=arguments)

    try:
        module_obj = import_module(name)
    except Exception as ex:
        return {'return_code': -2, 'std_err': 'Either module {} does not exist or there is some other problem. '
                                              'Original error: {}.'.format(name, ex)}

    try:
        executable = module_obj.validate
    except AttributeError:
        # validate function does not exist
        ret = {'return_code': -2, 'std_err': 'Module {} does not have validate function.'.format(name)}
    else:
        try:
            ret_val = executable(arguments)
            ret = {'return_code': ret_val, 'std_out': 'Module {} is valid.'.format(name)}
        except Exception as ex:
            ret = {'return_code': -1, 'std_err': 'Module {} is not valid. Original exception: {}'.format(name, ex)}

    logger.logger.info("Module validation finished", module_name=name, arguments=arguments, ret=ret)
    return ret


def import_module(module_path: str):
    """
    Import module specified by name. The module does not have to be installed,
    as the path is being added to the system PATH.
    :param module_path: path to the module directory relative to config.MODULES_DIR
    :return: imported module object
    """
    sys.path.insert(0, config.MODULES_DIR)

    module = module_path
    if not module.endswith('/'):
        module += '/'
    module += 'mod'

    try:
        module_obj = importlib.import_module(module)
    except ModuleNotFoundError as ex:
        raise ex

    return module_obj


def list_sessions(target_ip: str) -> list:
    """
    Get list of available session IDs for given target IP.
    :param target_ip: target IP
    :return: list of session IDs
    """
    client = MsfRpcClient(config.MSFRPCD_PASS, username=config.MSFRPCD_USERNAME,
                          port=config.MSFRPCD_PORT, ssl=config.MSFRPCD_SSL)

    sessions_list = list()
    for session_key, session_value in client.sessions.list.items():
        if session_value['target_host'] == target_ip or session_value['tunnel_peer'].split(':')[0] == target_ip:
            sessions_list.append(session_key)

    logger.logger.info("Listing sessions", target=target_ip, sessions_list=sessions_list)
    return sessions_list


def list_modules() -> list:
    """
    Get list of available modules.
    :return: list of available modules
    """
    default_modules_dir = config.MODULES_DIR
    # List all python files, exclude init files
    files = [f.replace(default_modules_dir, '') for f in glob.glob(default_modules_dir + "**/*.py", recursive=True)]
    files = list(filter(lambda a: a.find('__init__.py') == -1, files))

    logger.logger.info("Listing modules", modules_list=files)
    return files


def kill_execution() -> int:  # TODO: implement later on
    """
    Kill chosen execution.
    :return: return code
    """

    logger.logger.info("Killing execution")
    return -1


def get_file_content(file_path: str) -> bytes:
    """
    Get file binary content from path

    :param file_path: path to wanted file
    :return: binary content of the desired file
    """
    with open(file_path, 'rb') as bf:
        file_content = bf.read()

    return file_content


# schema file validation function
class File(object):
    """
    Utility function to combine validation directives in AND Boolean fashion.
    """

    def __init__(self, *args, **kw):
        self._args = args
        if not set(kw).issubset({"error", "schema", "ignore_extra_keys"}):
            diff = {"error", "schema", "ignore_extra_keys"}.difference(kw)
            raise TypeError("Unknown keyword arguments %r" % list(diff))
        self._error = kw.get("error")
        self._ignore_extra_keys = kw.get("ignore_extra_keys", False)
        # You can pass your inherited Schema class.
        self._schema = kw.get("schema", Schema)

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, ", ".join(repr(a) for a in self._args))

    def validate(self, data):
        """
        Validate data using defined sub schema/expressions ensuring all
        values are valid.
        :param data: to be validated with sub defined schemas.
        :return: returns validated data
        """
        for s in [self._schema(s, error=self._error, ignore_extra_keys=self._ignore_extra_keys) for s in self._args]:
            data = s.validate(data)
        if os.path.isfile(data):
            return data
        else:
            raise Exception("{} isn't valid file.".format(data))


# schema directory validation function
class Dir(object):
    """
    Utility function to combine validation directives in AND Boolean fashion.
    """

    def __init__(self, *args, **kw):
        self._args = args
        if not set(kw).issubset({"error", "schema", "ignore_extra_keys"}):
            diff = {"error", "schema", "ignore_extra_keys"}.difference(kw)
            raise TypeError("Unknown keyword arguments %r" % list(diff))
        self._error = kw.get("error")
        self._ignore_extra_keys = kw.get("ignore_extra_keys", False)
        # You can pass your inherited Schema class.
        self._schema = kw.get("schema", Schema)

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, ", ".join(repr(a) for a in self._args))

    def validate(self, data):
        """
        Validate data using defined sub schema/expressions ensuring all
        values are valid.
        :param data: to be validated with sub defined schemas.
        :return: returns validated data
        """
        for s in [self._schema(s, error=self._error, ignore_extra_keys=self._ignore_extra_keys) for s in self._args]:
            data = s.validate(data)
        if os.path.isdir(data):
            return data
        else:
            raise Exception("{} isn't valid directory.".format(data))

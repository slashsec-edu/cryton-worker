from cryton_worker.lib import util


def validate_module(body: dict) -> dict:
    """
    Event, when triggered validate requested module.
    :param body: Arguments for function
    :return: Result dictionary containing details about the job.
    """
    attack_module = body.get('attack_module')
    module_arguments = body.get('attack_module_arguments')
    result_dict = util.validate_module(attack_module, module_arguments)

    return result_dict


def list_modules(_: dict) -> dict:
    """
    Event, when triggered list all modules available on Worker.
    :param _: Arguments for function
    :return: Result dictionary containing details about the job.
    """
    result = util.list_modules()
    result_dict = {'module_list': result}

    return result_dict


def list_sessions(body: dict) -> dict:
    """
    Event, when triggered list all sessions.
    :param body: Arguments for function
    :return: Result dictionary containing details about the job.
    """
    target_ip = body.get('target_ip')
    result = util.list_sessions(target_ip)
    result_dict = {'session_list': result}

    return result_dict


def kill_execution(body: dict) -> dict:
    """
    Event, when triggered kill Step's Execution.
    :param body: Arguments for function
    :return: Result dictionary containing details about the job.
    """
    req_queue = body.get('request_queue')
    req_pipe = body.get('request_pipe')
    res_pipe = body.get('response_pipe')
    correlation_id = body.get('correlation_id')
    req_queue.put(('KILL', req_pipe, correlation_id))
    kill_code, kill_err = res_pipe.recv()

    result_dict = {'return_code': kill_code, 'std_err': kill_err}

    return result_dict


def health_check(_: dict) -> dict:
    """
    Event, when triggered check if Worker is OK.
    :param _: Arguments for function
    :return: Result dictionary containing details about the job.
    """
    result = 0
    result_dict = {'return_code': result}

    return result_dict

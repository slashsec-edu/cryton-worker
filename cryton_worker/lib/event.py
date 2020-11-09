from cryton_worker.lib import util


def process_event(event_t: str, body: dict) -> dict:
    """
    Decide what to do based on event
    :param event_t: Event type
    :param body: Event value
    :return: event result
    """
    if event_t == 'KILL_EXECUTION':
        event_v = event_kill_execution(body)

    elif event_t == 'VALIDATE_MODULE':
        event_v = event_validate_module(body)

    elif event_t == 'LIST_MODULES':
        event_v = event_list_modules(body)

    elif event_t == 'LIST_SESSIONS':
        event_v = event_list_sessions(body)

    elif event_t == 'HEALTHCHECK':
        event_v = event_health_check(body)

    else:
        event_v = {'return_code': -2}

    return event_v


def event_validate_module(body: dict) -> dict:
    """
    Event, when triggered validate requested module.
    :param body: Arguments for function
    :return: Result dictionary containing details about the job.
    """
    attack_module = body.get('attack_module')
    module_arguments = body.get('attack_module_arguments')
    result_dict = util.validate_module(attack_module, module_arguments)

    return result_dict


def event_list_modules(_: dict) -> dict:
    """
    Event, when triggered list all modules available on Worker.
    :param _: Arguments for function
    :return: Result dictionary containing details about the job.
    """
    result = util.list_modules()
    result_dict = {'module_list': result}

    return result_dict


def event_list_sessions(body: dict) -> dict:
    """
    Event, when triggered list all sessions.
    :param body: Arguments for function
    :return: Result dictionary containing details about the job.
    """
    target_ip = body.get('target_ip')
    result = util.list_sessions(target_ip)
    result_dict = {'session_list': result}

    return result_dict


def event_kill_execution(_: dict) -> dict:  # TODO: implement later
    """
    Event, when triggered kill Step's Execution.
    :param _: Arguments for function
    :return: Result dictionary containing details about the job.
    """
    result = util.kill_execution()
    result_dict = {'return_code': result}

    return result_dict


def event_health_check(_: dict) -> dict:  # TODO: implement later
    """
    Event, when triggered check if Worker is OK.
    :param _: Arguments for function
    :return: Result dictionary containing details about the job.
    """
    result = 0
    result_dict = {'return_code': result}

    return result_dict

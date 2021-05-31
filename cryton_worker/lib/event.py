from multiprocessing import Pipe

from cryton_worker.lib.util import util, constants as co, logger


class Event:
    def __init__(self, event_details: dict, main_queue: util.ManagerPriorityQueue):
        """
        Class for processing events.
        :param event_details: Received event details
        :param main_queue: Worker's queue for internal request processing
        """
        self._event_details = event_details
        self._main_queue = main_queue
        self._response_pipe, self._request_pipe = Pipe(False)

    def validate_module(self) -> dict:
        """
        Validate requested module.
        :return: Details about the event result
        """
        logger.logger.debug("Running event: validate_module", event_details=self._event_details)
        attack_module = self._event_details.get(co.ATTACK_MODULE)
        module_arguments = self._event_details.get(co.ATTACK_MODULE_ARGUMENTS)
        return util.validate_module(attack_module, module_arguments)

    def list_modules(self) -> dict:
        """
        List all modules available on Worker.
        :return: Details about the event result
        """
        logger.logger.debug("Running event: list_modules", event_details=self._event_details)
        result = util.list_modules()
        return {co.MODULE_LIST: result}

    def list_sessions(self) -> dict:
        """
        List all sessions available on Worker.
        :return: Details about the event result
        """
        logger.logger.debug("Running event: list_sessions", event_details=self._event_details)
        target_ip = self._event_details.get(co.TARGET_IP)
        result = util.Metasploit().get_target_sessions(target_ip)
        return {co.SESSION_LIST: result}

    def kill_step_execution(self) -> dict:
        """
        Kill Step's Execution (AttackTask) using correlation ID.
        :return: Details about the event result
        """
        logger.logger.debug("Running event: kill_step_execution", event_details=self._event_details)
        correlation_id = self._event_details.get(co.CORRELATION_ID)
        item = util.PrioritizedItem(co.MEDIUM_PRIORITY, {co.ACTION: co.ACTION_KILL_TASK,
                                                         co.RESULT_PIPE: self._request_pipe,
                                                         co.CORRELATION_ID: correlation_id})
        self._main_queue.put(item)
        return self._response_pipe.recv()

    def health_check(self) -> dict:
        """
        Check if Worker is UP and running.
        :return: Details about the event result
        """
        logger.logger.debug("Running event: health_check", event_details=self._event_details)
        result = 0
        return {co.RETURN_CODE: result}

    def start_trigger(self) -> dict:
        """
        Start Trigger.
        :return: Details about the event result
        """
        logger.logger.debug("Running event: start_trigger", event_details=self._event_details)
        item = util.PrioritizedItem(co.MEDIUM_PRIORITY, {co.ACTION: co.ACTION_START_TRIGGER,
                                                         co.RESULT_PIPE: self._request_pipe,
                                                         co.DATA: self._event_details})
        self._main_queue.put(item)
        return self._response_pipe.recv()

    def stop_trigger(self) -> dict:
        """
        Stop Trigger.
        :return: Details about the event result
        """
        logger.logger.debug("Running event: stop_trigger", event_details=self._event_details)
        item = util.PrioritizedItem(co.MEDIUM_PRIORITY, {co.ACTION: co.ACTION_STOP_TRIGGER,
                                                         co.RESULT_PIPE: self._request_pipe,
                                                         co.DATA: self._event_details})
        self._main_queue.put(item)
        return self._response_pipe.recv()

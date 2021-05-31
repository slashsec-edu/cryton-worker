from multiprocessing import Queue, Process, Lock
from typing import List, Any

from cryton_worker.lib.util import logger, constants as co, util


class Trigger:
    def __init__(self, host: str, port: int, main_queue: Queue):
        """
        Base class for Triggers.
        :param host: Trigger's host
        :param port: Trigger's port
        :param main_queue: Worker's queue for internal request processing
        """
        self._host = host
        self._port = port
        self._main_queue = main_queue
        self._process: Process or None = None
        self._activators: List[dict] = []
        self._activators_lock = Lock()  # Lock to prevent modifying, while performing time consuming actions.

    def compare_identifiers(self, t_type: Any, t_host: str, t_port: int) -> bool:
        """
        Check if specified identifiers match with Trigger's.
        :param t_type: Trigger's type
        :param t_host: Trigger's host
        :param t_port: Trigger's port
        :return: True if identifiers match Trigger's
        """
        if isinstance(self, t_type) and self._host == t_host and self._port == t_port:
            return True
        return False

    def start(self) -> None:
        """
        Start the Trigger.
        :return: None
        """
        pass

    def stop(self) -> None:
        """
        Stop the Trigger.
        :return: None
        """
        pass

    def add_activator(self, details: dict) -> None:
        """
        Add activator.
        :param details: Activator options
        :return: None
        """
        pass

    def remove_activator(self, details: dict) -> None:
        """
        Remove activator.
        :param details: Activator options
        :return: None
        """
        pass

    def any_activator_exists(self) -> bool:
        """
        Check if Trigger activators are empty.
        :return: True if Trigger has no activators
        """
        return False if len(self._activators) == 0 else True

    def _notify(self, queue_name: str, message_body: dict) -> None:
        """
        Send message to reply_to about successful trigger call.
        :param queue_name: Target queue (message receiver)
        :param message_body: Message content
        :return: None
        """
        logger.logger.debug("Notifying about successful trigger call.", host=self._host, port=self._port,
                            trigger_type=self.__class__)
        item = util.PrioritizedItem(co.HIGH_PRIORITY, {co.ACTION: co.ACTION_SEND_MESSAGE, co.QUEUE_NAME: queue_name,
                                                       co.DATA: message_body, co.PROPERTIES: {}})
        self._main_queue.put(item)

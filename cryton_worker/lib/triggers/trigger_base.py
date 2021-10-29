import uuid
from multiprocessing import Queue, Process, Lock
from typing import List, Any, Optional

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

    def compare_identifiers(self, trigger_type: Any, trigger_host: str, trigger_port: int) -> bool:
        """
        Check if specified identifiers match with Trigger's.
        :param trigger_type: Trigger's type
        :param trigger_host: Trigger's host
        :param trigger_port: Trigger's port
        :return: True if identifiers match Trigger's
        """
        if isinstance(self, trigger_type) and self._host == trigger_host and self._port == trigger_port:
            return True
        return False

    def find_activator(self, trigger_id: str) -> Optional[dict]:
        """
        Check if specified identifiers match with Trigger's.
        :param trigger_id: Trigger's ID
        :return: Activator if found, else None
        """
        with self._activators_lock:
            for activator in self._activators:
                if activator.get(co.TRIGGER_ID) == trigger_id:
                    return activator
        return None

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

    def get_activators(self) -> List[dict]:
        """
        Get list of all activators.
        :return: Trigger's activators
        """
        with self._activators_lock:
            return self._activators

    def any_activator_exists(self) -> bool:
        """
        Check if Trigger activators are empty.
        :return: True if Trigger has no activators
        """
        return False if len(self._activators) == 0 else True

    @staticmethod
    def _generate_id() -> uuid.UUID:
        return uuid.uuid1()

    def _notify(self, queue_name: str, message_body: dict) -> None:
        """
        Send message to reply_to about successful trigger call.
        :param queue_name: Target queue (message receiver)
        :param message_body: Message content
        :return: None
        """
        print(f"Notifying about successful trigger call. host: {self._host} port: {self._port} "
              f"trigger_type: {self.__class__}")
        logger.logger.debug("Notifying about successful trigger call.", host=self._host, port=self._port,
                            trigger_type=self.__class__)
        item = util.PrioritizedItem(co.HIGH_PRIORITY, {co.ACTION: co.ACTION_SEND_MESSAGE, co.QUEUE_NAME: queue_name,
                                                       co.DATA: message_body, co.PROPERTIES: {}})
        self._main_queue.put(item)

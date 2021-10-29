import bottle
from multiprocessing import Queue, Process
from typing import Optional

from cryton_worker.lib.util import logger, constants as co
from cryton_worker.lib.triggers.trigger_base import Trigger


class HTTPTrigger(Trigger):
    def __init__(self, host: str, port: int, main_queue: Queue):
        """
        Class for HTTPTriggers (wrapper for Bottle).
        :param host: Trigger's host
        :param port: Trigger's port
        :param main_queue: Worker's queue for internal request processing
        """
        super().__init__(host, port, main_queue)
        self._app = bottle.Bottle()
        self._stopped = True

    def add_activator(self, details: dict) -> str:
        """
        Add activator to Trigger and restart it.
        :param details: Activator options
            Example:
            {
                "host": str,
                "port": int,
                "reply_to": str,
                "routes": [
                    {
                        "path": str,
                        "method": str,
                        "parameters": [
                            {"name": str, "value": str},
                        ]
                    }
                ]
            }
        :return: ID of the new activator
        """
        logger.logger.debug("Adding activator to HTTPTrigger.", host=self._host, port=self._port, details=details)
        activator_id = str(self._generate_id())
        details.update({co.TRIGGER_ID: activator_id})

        with self._activators_lock:
            self._activators.append(details)
            self._restart()
        return activator_id

    def remove_activator(self, activator: dict) -> None:
        """
        Remove activator from Trigger and restart it.
        :param activator: Desired activator
        :return: None
        """
        logger.logger.debug("Removing activator from HTTPTrigger.", host=self._host, port=self._port,
                            activator_id=activator.get(co.TRIGGER_ID))
        with self._activators_lock:
            self._activators.remove(activator)
            self._restart()

    def _restart(self) -> None:
        """
        Stop the App, reload activators and start the App again.
        :return: None
        """
        logger.logger.debug("Restarting HTTPTrigger.", host=self._host, port=self._port)
        if self.any_activator_exists():  # If there are no active activators, only call stop.
            if not self._stopped:
                self.stop()
                self._app = bottle.Bottle()  # Discard old Bottle instance if adding more activators.

            for activator in self._activators:  # Feed routes to the App again after discarding.
                for route in activator.get("routes"):
                    self._app.route(route.get("path"), method=route.get("method"), callback=self._handle_request)
            self.start()

        else:
            if not self._stopped:
                self.stop()

    def _handle_request(self) -> None:
        """
        Handle HTTPTrigger request (call) (check path, method and parameters).
        :return: None
        """
        path = bottle.request.path
        logger.logger.debug("Handling HTTPTrigger request", host=self._host, port=self._port, path=path)

        with self._activators_lock:
            for activator in self._activators:
                for route in activator.get("routes"):  # For each route check path, method and parameters.
                    if route.get("path") == path and route.get("method") == bottle.request.method:
                        request_parameters = self._check_parameters(route.get("parameters"))
                        if request_parameters is not None:
                            message_body = {
                                co.EVENT_T: co.EVENT_TRIGGER_STAGE,
                                co.EVENT_V: {co.TRIGGER_ID: activator.get(co.TRIGGER_ID),
                                             co.TRIGGER_PARAMETERS: request_parameters}
                            }
                            self._notify(activator.get(co.REPLY_TO), message_body)

    @staticmethod
    def _check_parameters(parameters: list) -> Optional[dict]:
        """
        Check if requested parameters are correct.
        :param parameters: Parameters to check
        :return: Request's parameters if they match given parameters
        """
        logger.logger.debug("Checking parameters.", parameters=parameters)
        if bottle.request.method == "GET":
            request_parameters = bottle.request.query
            for param in parameters:
                if str(request_parameters.get(param.get("name"))) != str(param.get("value")):  # Bad value.
                    return None

        elif bottle.request.method == "POST":
            request_parameters = bottle.request.forms
            for param in parameters:
                if str(request_parameters.get(param.get("name"))) != str(param.get("value")):  # Bad value.
                    return None

        else:
            return None

        request_parameters_dict = {}  # Create dictionary from bottle.FormsDict, otherwise json.dumps would fail
        for key, value in request_parameters.items():
            request_parameters_dict.update({key: value})
        return request_parameters_dict

    def start(self) -> None:
        """
        Start the Trigger.
        :return: None
        """
        if self._stopped:
            print(f"Starting HTTPTrigger. host: {self._host} port: {self._port}")
            logger.logger.debug("Starting HTTPTrigger.", host=self._host, port=self._port)
            self._process = Process(target=self._app.run,
                                    kwargs={co.TRIGGER_HOST: self._host, co.TRIGGER_PORT: self._port, "quiet": True})
            self._process.start()
            self._stopped = False

    def stop(self) -> None:
        """
        Stop the Trigger.
        :return: None
        """
        if not self._stopped:
            print(f"Stopping HTTPTrigger. host: {self._host} port: {self._port}")
            logger.logger.debug("Stopping HTTPTrigger.", host=self._host, port=self._port)
            self._app.close()
            self._process.terminate()
            self._process = None
            self._stopped = True

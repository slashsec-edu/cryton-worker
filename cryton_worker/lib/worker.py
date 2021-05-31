from typing import List
from threading import Thread
from multiprocessing import Lock
import time
import traceback

from cryton_worker.lib import consumer
from cryton_worker.lib.util import constants as co, logger, util
from cryton_worker.lib.triggers import Trigger, TriggerEnum


class Worker:
    def __init__(self, rabbit_host: str, rabbit_port: int, rabbit_username: str, rabbit_password: str, prefix: str,
                 consumer_count: int, processor_count: int, max_retries: int, persistent: bool):
        """
        Worker processes internal requests using self._main_queue and communicates with RabbitMQ server using Consumer.
        :param rabbit_host: Rabbit's server port
        :param rabbit_port: Rabbit's server host
        :param rabbit_username: Rabbit's username
        :param rabbit_password: Rabbit's password
        :param prefix: Worker prefix for queues
        :param consumer_count: How many consumers to use for queues
        (higher == faster RabbitMQ requests consuming, but heavier processor usage)
        :param processor_count: How many processors to use for internal requests
        (higher == more responsive internal requests processing, but heavier processor usage)
        :param max_retries: How many times to try to connect
        :param persistent: Keep Worker alive and keep on trying forever (if True)
        """
        self._triggers: List[Trigger] = []
        self._triggers_lock = Lock()  # Lock to prevent modifying, while performing time consuming actions.
        self._stopped = False
        self._main_queue: util.ManagerPriorityQueue = util.get_manager().PriorityQueue()
        self._processor_count = processor_count if processor_count > 0 else 1
        self._consumer = consumer.Consumer(self._main_queue, rabbit_host, rabbit_port, rabbit_username, rabbit_password,
                                           prefix, consumer_count, max_retries, persistent)

    def start(self) -> None:
        """
        Start Consumer and processors in thread and keep self alive.
        :return: None
        """
        logger.logger.debug("Worker started.", processor_count=self._processor_count, consumer=str(self._consumer))
        print("Starting..")
        print("To exit press CTRL+C")
        try:
            self._start_consumer()
            self._start_threaded_processors()
            while not self._stopped and not self._consumer.stopped:  # Keep self alive and check for stops.
                time.sleep(5)

        except KeyboardInterrupt:
            pass
        self.stop()

    def stop(self) -> None:
        """
        Stop Worker (self). Stop Consumer, processors and triggers.
        :return: None
        """
        logger.logger.info("Stopping Worker", processor_count=self._processor_count, consumer=str(self._consumer))
        print("Exiting..")
        self._consumer.stop()
        self._stopped = True  # Giving time to self._consumer for proper stop.
        self._stop_threaded_processors()
        self._stop_triggers()

    def _start_threaded_processors(self) -> None:
        """
        Start processors in thread.
        :return: None
        """
        logger.logger.debug("Starting threaded processors.", processor_count=self._processor_count)
        for i in range(self._processor_count):
            thread = Thread(target=self._threaded_processor, kwargs={"thread_id": i + 1}, name=f"Thread-{i}-processor")
            thread.start()

    def _stop_threaded_processors(self) -> None:
        """
        Stop processors by sending shutdown request.
        :return: None
        """
        logger.logger.debug("Stopping threaded processors.", processor_count=self._processor_count)
        for _ in range(self._processor_count):
            item = util.PrioritizedItem(co.LOW_PRIORITY, {co.ACTION: co.ACTION_SHUTDOWN_THREADED_PROCESSOR})
            self._main_queue.put(item)

    def _start_consumer(self) -> None:
        """
        Start Consumer in thread.
        :return: None
        """
        logger.logger.debug("Starting self._consumer in Thread.", consumer=str(self._consumer))
        thread = Thread(target=self._consumer.start)
        thread.start()

    def _stop_triggers(self) -> None:
        """
        Stop all Triggers in self._triggers.
        :return: None
        """
        logger.logger.debug("Stopping all Triggers.")
        with self._triggers_lock:
            while len(self._triggers) > 0:
                trigger_obj = self._triggers.pop(-1)
                trigger_obj.stop()

    def _threaded_processor(self, thread_id: int) -> None:
        """
        Start a processor for request processing.
        :param thread_id: Fictional thread (processor) ID
        :return: None
        """
        logger.logger.debug("Threaded processor started.", thread_id=thread_id)
        while not self._stopped:
            request: util.PrioritizedItem = self._main_queue.get()
            request_action = request.item.pop(co.ACTION)

            try:  # Try to get method reference.
                action_callable = getattr(self, request_action)
            except AttributeError:
                if request_action == co.ACTION_SHUTDOWN_THREADED_PROCESSOR:
                    logger.logger.debug("Shutting down threaded processor.", thread_id=thread_id)
                    break
                logger.logger.warning("Request contains unknown action.", request=request)
                continue

            try:  # Try to call method and process the request.
                action_callable(request.item)
            except Exception as ex:
                logger.logger.warning("Request threw an exception in the process.", request=request, error=str(ex))
                logger.logger.debug("Request threw an exception in the process.", request=request, error=str(ex),
                                    traceback=traceback.format_exc())
                continue

        logger.logger.debug("Threaded processor stopped.", thread_id=thread_id)

    def _kill_task(self, request: dict) -> None:
        """
        Process; Kill running Task using correlation_id.
        :param request: Data needed for process (Must contain: co.RESULT_PIPE, co.CORRELATION_ID)
        :return: None
        """
        logger.logger.debug("Calling process _kill_task", request=request)
        result_pipe = request.pop(co.RESULT_PIPE)
        correlation_id = request.pop(co.CORRELATION_ID)

        task_obj = self._consumer.pop_task(correlation_id)
        if task_obj is None:  # Task doesn't exist.
            err = "Couldn't find the Task."
            logger.logger.debug(err, task_correlation_id=correlation_id)
            result = {co.RETURN_CODE: co.CODE_ERROR, co.STD_ERR: err}

        else:  # Task found.
            try:
                task_obj.kill()
                result = {co.RETURN_CODE: co.CODE_OK}

            except Exception as ex:
                logger.logger.debug("Couldn't kill the Task.", task_correlation_id=correlation_id, error=str(ex))
                result = {co.RETURN_CODE: co.CODE_ERROR, co.STD_ERR: str(ex)}

        result_pipe.send(result)
        logger.logger.debug("Finished process _kill_task", result=result)

    def _finish_task(self, request: dict) -> None:
        """
        Process; Delete Task from Consumer's Tasks list.
        :param request: Data needed for process (Must contain: co.CORRELATION_ID)
        :return: None
        """
        logger.logger.debug("Calling process _finish_task", request=request)
        correlation_id = request.pop(co.CORRELATION_ID)
        data = request.pop(co.DATA)

        task_obj = self._consumer.pop_task(correlation_id)
        task_obj.reply(data)
        logger.logger.debug("Finished process _finish_task")

    def _send_message(self, request: dict) -> None:
        """
        Process; Use Consumer to send a message.
        :param request: Data needed for process (Must contain: co.QUEUE_NAME, co.DATA, co.PROPERTIES)
        :return: None
        """
        logger.logger.debug("Calling process _send_message", request=request)
        queue_name = request.pop(co.QUEUE_NAME)
        msg_body = request.pop(co.DATA)
        msg_properties = request.pop(co.PROPERTIES)

        msg_properties.update(co.DEFAULT_MSG_PROPERTIES)
        self._consumer.send_message(queue_name, msg_body, msg_properties)
        logger.logger.debug("Finished process _send_message")

    def _start_trigger(self, request: dict) -> None:
        """
        Process; Start Trigger.
        :param request: Data needed for process (Must contain: co.RESULT_PIPE, co.DATA)
        :return: None
        """
        logger.logger.debug("Calling process _start_trigger", request=request)
        result_pipe = request.pop(co.RESULT_PIPE)
        data = request.pop(co.DATA)

        t_host, t_port, t_type = data.get(co.T_HOST), data.get(co.T_PORT), TriggerEnum[data.get(co.T_TYPE)]
        with self._triggers_lock:  # Try to find specified Trigger.
            for trigger_obj in self._triggers:
                if trigger_obj.compare_identifiers(t_type, t_host, t_port):
                    logger.logger.debug("Found existing Trigger", host=t_host, port=t_port, type=t_type)
                    break
            else:  # If Trigger doesn't exist, create new one.
                logger.logger.debug("Creating new Trigger", host=t_host, port=t_port, type=t_type)
                trigger_obj = t_type(t_host, t_port, self._main_queue)
                self._triggers.append(trigger_obj)

        try:  # Add activator for Trigger.
            trigger_obj.add_activator(data)
        except Exception as ex:
            result = {co.RETURN_CODE: co.CODE_ERROR, co.STD_ERR: str(ex)}
        else:
            result = {co.RETURN_CODE: co.CODE_OK}

        result_pipe.send(result)
        logger.logger.debug("Finished process _start_trigger", result=result)

    def _stop_trigger(self, request: dict) -> None:
        """
        Process; Stop Trigger.
        :param request: Data needed for process (Must contain: co.RESULT_PIPE, co.DATA)
        :return: None
        """
        logger.logger.debug("Calling process _stop_trigger", request=request)
        result_pipe = request.pop(co.RESULT_PIPE)
        data = request.pop(co.DATA)

        t_host, t_port, t_type = data.get(co.T_HOST), data.get(co.T_PORT), TriggerEnum[data.get(co.T_TYPE)]
        with self._triggers_lock:  # Try to find specified Trigger.
            for trigger_obj in self._triggers:
                if trigger_obj.compare_identifiers(t_type, t_host, t_port):
                    logger.logger.debug("Found existing Trigger", host=t_host, port=t_port, type=t_type)
                    break
            else:  # If Trigger doesn't exist, create new one.
                logger.logger.debug("Existing Trigger not found", host=t_host, port=t_port, type=t_type)
                trigger_obj = None

        try:  # Remove activator from Trigger. Optionally remove it completely.
            trigger_obj.remove_activator(data)
            if not trigger_obj.any_activator_exists():
                with self._triggers_lock:
                    self._triggers.remove(trigger_obj)

        except AttributeError:
            result = {co.RETURN_CODE: co.CODE_ERROR, co.STD_ERR: "Trigger not found."}
        except Exception as ex:
            result = {co.RETURN_CODE: co.CODE_ERROR, co.STD_ERR: str(ex)}
        else:
            result = {co.RETURN_CODE: co.CODE_OK}

        result_pipe.send(result)
        logger.logger.debug("Finished process _stop_trigger", result=result)

from multiprocessing import Process
import amqpstorm
import json
import traceback
from schema import Schema, Or, SchemaError

from cryton_worker.lib import event
from cryton_worker.lib.util import util, constants as co, logger


class Task:
    def __init__(self, message: amqpstorm.Message, main_queue: util.ManagerPriorityQueue):
        """
        Class for processing callbacks.
        :param message: Received RabbitMQ Message
        :param main_queue: Worker's queue for internal request processing
        """
        self.message = message
        self.correlation_id = self.message.correlation_id
        self._main_queue = main_queue
        self._process = Process(target=self)

    def __call__(self) -> None:
        """
        Load message, execute callback and send reply.
        :return: None
        """
        logger.logger.debug("Processing Task.", correlation_id=self.correlation_id)
        print(f"Processing Task. correlation_id: {self.correlation_id}")
        self.message.ack()

        message_body = json.loads(self.message.body)
        try:
            self._validate(message_body)
        except SchemaError as ex:
            result = {co.RETURN_CODE: co.CODE_ERROR, co.STD_ERR: str(ex)}
        else:
            result = self._execute(message_body)

        result_json = json.dumps(result)
        item = util.PrioritizedItem(co.HIGH_PRIORITY, {co.ACTION: co.ACTION_FINISH_TASK, co.DATA: result_json,
                                                       co.CORRELATION_ID: self.correlation_id})
        self._main_queue.put(item)
        print(f"Finished Task processing. correlation_id: {self.correlation_id}")
        logger.logger.debug("Finished Task processing.", correlation_id=self.correlation_id)

    def _execute(self, message_body: dict) -> dict:
        """
        Custom execution for callback processing.
        :param message_body: Received RabbitMQ Message's
        :return: Execution's result
        """
        pass

    def _validate(self, message_body: dict) -> dict:
        """
        Custom validation for callback processing.
        :param message_body: Received RabbitMQ Message's
        :return: Validation's result
        """
        pass

    def kill(self) -> None:
        """
        Wrapper method for Process.kill() and send reply.
        :return: None
        """
        logger.logger.debug("Killing Task (its process).", correlation_id=self.correlation_id)
        self._process.kill()

        result = {co.RETURN_CODE: co.CODE_KILL}
        result_json = json.dumps(result)
        self.reply(result_json)

    def join(self) -> None:
        """
        Wrapper method for Process.join().
        :return: None
        """
        logger.logger.debug("Waiting for Task to end.", correlation_id=self.correlation_id)
        self._process.join()

    def start(self) -> None:
        """
        Wrapper method for Process.start().
        :return: None
        """
        logger.logger.debug("Starting Task in a process.", correlation_id=self.correlation_id)
        self._process.start()

    def reply(self, message_content: str) -> None:
        """
        Update properties and send message containing response to reply_to.
        :param message_content: Content to be sent inside of the message
        :return: None
        """
        logger.logger.debug("Sending reply.", correlation_id=self.correlation_id, reply_to=self.message.reply_to,
                            message_body=message_content)
        self.message.channel.queue.declare(self.message.reply_to)
        self.message.properties.update(co.DEFAULT_MSG_PROPERTIES)

        response = amqpstorm.Message.create(self.message.channel, message_content, self.message.properties)
        response.publish(self.message.reply_to)
        logger.logger.debug("Reply sent.", correlation_id=self.correlation_id)


class AttackTask(Task):
    def __init__(self, message: amqpstorm.Message, main_queue: util.ManagerPriorityQueue):
        """
        Class for processing attack callbacks.
        :param message: Received RabbitMQ Message
        :param main_queue: Worker's queue for internal request processing
        """
        super().__init__(message, main_queue)

    def _validate(self, message_body: dict) -> None:
        """
        Custom validation for callback processing.
        :param message_body: Received RabbitMQ Message's
        :return: None
        """
        validation_schema = Schema({
            co.ACK_QUEUE: str,
            co.ATTACK_MODULE: str,
            co.ATTACK_MODULE_ARGUMENTS: dict
        })

        validation_schema.validate(message_body)

    def _execute(self, message_body: dict) -> dict:
        """
        Custom execution for attack callback processing.
        Confirm that message was received, update properties and execute module.
        :param message_body: Received RabbitMQ Message's
        :return: Execution's result
        """
        logger.logger.info("Running AttackTask._execute().", correlation_id=self.correlation_id)

        # Confirm message was received.
        ack_queue = message_body.pop(co.ACK_QUEUE)
        msg_body = {co.RETURN_CODE: co.CODE_OK, co.CORRELATION_ID: self.correlation_id}
        item = util.PrioritizedItem(co.HIGH_PRIORITY, {co.ACTION: co.ACTION_SEND_MESSAGE, co.DATA: msg_body,
                                                       co.QUEUE_NAME: ack_queue, co.PROPERTIES: {}})
        self._main_queue.put(item)

        # Extract needed data.
        module_name = message_body.pop(co.ATTACK_MODULE)
        module_arguments = message_body.pop(co.ATTACK_MODULE_ARGUMENTS)

        # Start module execution.
        result = util.run_module(module_name, module_arguments)
        logger.logger.info("Finished AttackTask._execute().", correlation_id=self.correlation_id)
        return result


class ControlTask(Task):
    def __init__(self, message: amqpstorm.Message, main_queue: util.ManagerPriorityQueue):
        """
        Class for processing control callbacks.
        :param message: Received RabbitMQ Message
        :param main_queue: Worker's queue for internal request processing
        """
        super().__init__(message, main_queue)

    def _validate(self, message_body: dict) -> None:
        """
        Custom validation for callback processing.
        :param message_body: Received RabbitMQ Message's
        :return: None
        """
        validation_schema = Schema({
            co.EVENT_T: str,
            co.EVENT_V: Or(
                co.EVENT_VALIDATE_MODULE_SCHEMA, co.EVENT_LIST_MODULES_SCHEMA, co.EVENT_LIST_SESSIONS_SCHEMA,
                co.EVENT_KILL_STEP_EXECUTION_SCHEMA, co.EVENT_HEALTH_CHECK_SCHEMA, co.EVENT_START_TRIGGER_HTTP_SCHEMA,
                co.EVENT_START_TRIGGER_MSF_SCHEMA, co.EVENT_STOP_TRIGGER_SCHEMA, co.EVENT_LIST_TRIGGERS_SCHEMA
            )
        })

        validation_schema.validate(message_body)

    def _execute(self, message_body: dict) -> dict:
        """
        Custom execution for control callback processing.
        Process control event.
        :param message_body: Received RabbitMQ Message's
        :return: Execution's result
        """
        logger.logger.info("Running ControlTask._execute().", correlation_id=self.correlation_id)
        event_t = message_body.pop(co.EVENT_T)
        event_obj = event.Event(message_body.pop(co.EVENT_V), self._main_queue)

        try:  # Get event callable and execute it.
            event_t_lower = event_t.lower()
            event_obj_method = getattr(event_obj, event_t_lower)
        except AttributeError:
            ex = f"Unknown event type: {event_t}."
            event_v = {co.RETURN_CODE: co.CODE_ERROR, co.STD_ERR: ex}
            logger.logger.debug(ex, correlation_id=self.correlation_id)
        else:
            try:
                event_v = event_obj_method()
            except Exception as ex:
                event_v = {co.STD_ERR: {"ex_type": str(ex.__class__), "error": ex.__str__(),
                                        "traceback": traceback.format_exc()}}

        logger.logger.info("Finished ControlTask._execute().", correlation_id=self.correlation_id)
        return {co.EVENT_T: event_t, co.EVENT_V: event_v}

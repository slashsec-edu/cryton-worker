from typing import Tuple
from cryton_worker.lib import event, util
from cryton_worker.etc import config
from cryton_worker.lib import logger
import datetime
import json
import amqpstorm
import subprocess
import os
import sys
from threading import Thread
from multiprocessing import Process, Queue, Pipe
from queue import Empty
import time


class Task:
    def __init__(self, message: amqpstorm.Message, req_queue: Queue):
        """
        Class for processing callbacks.
        :param message: RabbitMQ Message
        :param req_queue: Queue for requests
        """
        self.message = message
        self.correlation_id = self.message.correlation_id
        self.req_queue = req_queue

    def __call__(self) -> None:
        """
        Rabbit callback for executing custom callbacks and sending responses.
        :return: None
        """
        self.message.ack()
        message_body = json.loads(self.message.body)
        ret = self._decide_callback(message_body)
        ret_msg = json.dumps(ret)

        self.req_queue.put(('FREE', self.correlation_id, ret_msg))

        return None

    def send_response(self, ret_msg: str) -> None:
        """
        Update properties and send message containing response to reply_to.
        :param ret_msg: Response from callback
        :return: None
        """
        self.message.channel.queue.declare(self.message.reply_to)
        self.message.properties.update({'content_encoding': 'utf-8'})
        self.message.properties.update({'timestamp': datetime.datetime.now()})

        response = amqpstorm.Message.create(self.message.channel, ret_msg, self.message.properties)
        response.publish(self.message.reply_to)

        return None

    def _decide_callback(self, message_body: dict) -> dict:
        """
        Decide what callback to run.
        :param message_body: RabbitMQ Message body
        :return: Dictionary containing results
        """
        if message_body.get('attack_module') is not None:
            logger.logger.info('Using attack.callback to process the request.', message_content=message_body)
            ret = callback_attack(message_body)

        elif message_body.get('event_t') is not None:
            logger.logger.info('Using attack.callback to process the request.', message_content=message_body)
            res_pipe, req_pipe = Pipe(False)
            message_body.update({'request_queue': self.req_queue, 'request_pipe': req_pipe, 'response_pipe': res_pipe})
            ret = callback_control(message_body)

        else:
            logger.logger.warning('Cannot process the request.', message_content=message_body)
            ret = {'err': 'Unknown request, \'attack_module\' or \'event_t\' must be defined.'}

        return ret


class Worker:
    def __init__(self, rabbit_host: str, rabbit_port: int, rabbit_username: str, rabbit_password: str,
                 consumer_count: int, queues: tuple, max_retries: int = 3, persistent: bool = False):
        """
        Worker.
        """
        self.hostname = rabbit_host
        self.port = rabbit_port
        self.username = rabbit_username
        self.password = rabbit_password
        self.max_retries = max_retries
        self.persistent = persistent
        self.queues = queues

        if consumer_count <= 0:
            consumer_count = 1

        self.consumer_count = consumer_count
        self._tasks = {}
        self.stopped = False
        self._connection: amqpstorm.Connection or None = None
        self.req_queue = Queue()
        logger.logger.debug(
            'Worker created.', rabbit_hostname=self.hostname, rabbit_port=self.port, consumer_count=self.consumer_count,
            max_retries=self.max_retries, queues=self.queues, persistent=self.persistent)

    def start(self) -> None:
        """
        Establish connection, start consumers and keep Worker alive.
        :return: None
        """
        print('Worker starting.. press CTRL + C to exit')
        self.stopped = False

        while not self.stopped:
            try:
                if self._update_connection():
                    self._update_consumers()
                self._process_pipe()  # times out after 5 seconds if there is no input
            except KeyboardInterrupt:
                print('Stopping Worker..')
                self.stop()
            except amqpstorm.AMQPConnectionError as ex:
                print(str(ex))
                if self.persistent:
                    print('Due to persistent mode, Worker will try to reconnect util manual shutdown.')
                    continue
                print('Stopping Worker..')
                self.stop()

        return None

    def _update_connection(self) -> bool:
        """
        Check connection for errors and refresh it.
        :raises: amqpstorm.AMQPConnectionError if connection cannot be open
        :return: True if connection was updated
        """
        try:
            if self._connection is None:
                raise amqpstorm.AMQPConnectionError('Connection does not exist.')
            self._connection.check_for_errors()
            if not self._connection.is_open:
                connection_error = amqpstorm.AMQPConnectionError('Connection is closed.')
                print('Connection to RabbitMQ lost.')
                logger.logger.warning(connection_error)
                raise connection_error

            return False

        except amqpstorm.AMQPError:
            self._create_connection()

        return True

    def _update_consumers(self) -> None:
        """
        Start consumers.
        :return: None
        """
        for _ in range(self.consumer_count):
            thread = Thread(target=self.consumer)
            thread.start()

        return None

    def _process_pipe(self) -> None:
        """
        Check for internal requests and process them.
        :return: None
        """
        try:
            request = self.req_queue.get(timeout=5)  # raises Empty after timeout

            if request[0] == 'KILL':
                req_type, res_pipe, correlation_id = request
                ret = self._kill(correlation_id)
                res_pipe.send(ret)

            elif request[0] == 'FREE':
                req_type, correlation_id, ret_msg = request
                task = self._get_task(correlation_id)
                task.send_response(ret_msg)
                self._tasks.pop(task)

            else:
                logger.logger.warning('Unknown request in queue.', request=request)

        except Empty:
            pass
        except Exception as ex:
            logger.logger.warning('Error parsing request from queue.', error=str(ex))

        return None

    def consumer(self) -> None:
        """
        Start a consumer (balancer) for faster queues consuming.
        :return: None
        """
        channel = self._connection.channel()
        channel.basic.qos(1)
        for queue in self.queues:  # consume on each queue
            channel.queue.declare(queue)
            channel.basic.consume(self._process_callback, queue)
        channel.start_consuming()

        return None

    def _process_callback(self, message: amqpstorm.Message) -> None:
        """
        Create TaskProcessor for new callback, start it in a Process and save it.
        :param message: RabbitMQ Message.
        :return: None
        """
        task = Task(message, self.req_queue)
        process = Process(target=task)
        process.start()
        self._tasks.update({task: process})

        return None

    def _get_task(self, correlation_id: str) -> Task or None:
        """
        Find a task.
        :param correlation_id: Task's correlation ID
        :return: Desired Task or nothing if it doesn't exist
        """
        for task in self._tasks.keys():
            if task.correlation_id is not None and task.correlation_id == correlation_id:
                return task
        return None

    def stop(self) -> None:
        """
        Stop Worker and it's consumers.
        :return: None
        """
        self.stopped = True

        try:
            print('Waiting for executed modules to finish.. press CTRL + C to kill them.')
            while len(self._tasks) > 0:
                task, task_process = self._tasks.popitem()
                try:
                    task_process.join()
                except KeyboardInterrupt:
                    task_process.kill()
                    raise KeyboardInterrupt

        except KeyboardInterrupt:
            print('Forcefully killing executed modules..')
            while len(self._tasks) > 0:
                task, task_process = self._tasks.popitem()
                task_process.kill()

        if self._connection is not None and self._connection.is_open:
            for channel in list(self._connection.channels.values()):
                channel.close()
            self._connection.close()

        return None

    def _kill(self, correlation_id) -> Tuple[int, str]:
        """
        Kill running module execution and send its response.
        :param correlation_id: Task's correlation ID
        :return: Tuple containing code and error message
        """
        task = self._get_task(correlation_id)

        # if the task doesn't exist
        if task is None:
            logger.logger.warning('Couldn\'t find (kill) the task.', task_correlation_id=correlation_id)
            return -1, 'not found'

        try:
            self._tasks.pop(task).kill()
        except Exception as ex:
            logger.logger.warning('Couldn\'t kill the task.', task_correlation_id=correlation_id)
            return -2, str(ex)

        # if the task is successfully killed, send a response
        ret_msg = {'return_code': -3}
        task.send_response(json.dumps(ret_msg))
        logger.logger.debug('Successfully killed the task.', task_correlation_id=correlation_id)

        return 0, ''

    def _create_connection(self) -> None:
        """
        Create a Rabbit connection.
        :return: None
        """
        attempts = 1
        while True:
            attempts += 1
            if self.stopped:
                break
            try:
                self._connection = amqpstorm.Connection(self.hostname, self.username, self.password, self.port)
                print('Connection to RabbitMQ established.')
                break
            except amqpstorm.AMQPError as ex:
                logger.logger.warning(ex)
                if self.max_retries and attempts > self.max_retries:
                    logger.logger.error('Max number of retries reached.')
                    raise amqpstorm.AMQPConnectionError('Max number of retries reached.')
                time.sleep(min(attempts * 2, 30))

        return None


def callback_attack(message_body: dict) -> dict:
    """
    Callback function for executing modules.
    :param message_body: RabbitMQ Message body.
    :return: Response containing details about the job.
    """
    module_name = message_body.get('attack_module')
    module_arguments = message_body.get('attack_module_arguments')
    ret = util.execute_module(module_name, module_arguments)

    return ret


def callback_control(message_body: dict) -> dict:
    """
    Callback function for processing control events.
    :param message_body: RabbitMQ Message body.
    :return: Response containing details about the job.
    """
    event_t = message_body.pop('event_t')

    if event_t == 'KILL_EXECUTION':
        event_v = event.kill_execution(message_body)

    elif event_t == 'VALIDATE_MODULE':
        event_v = event.validate_module(message_body)

    elif event_t == 'LIST_MODULES':
        event_v = event.list_modules(message_body)

    elif event_t == 'LIST_SESSIONS':
        event_v = event.list_sessions(message_body)

    elif event_t == 'HEALTHCHECK':
        event_v = event.health_check(message_body)

    else:
        event_v = {'return_code': -2}

    return {'event_t': event_t, 'event_v': event_v}


def start(rabbit_host: str, rabbit_port: int, rabbit_username: str, rabbit_password: str, prefix: str,
          consumer_count: int, max_retries: int, persistent: bool) -> None:
    """
    Creates Worker which connects to Rabbit server and listens for new messages.
    :param rabbit_host: Rabbit server host
    :param rabbit_port: Rabbit server port
    :param rabbit_username: Rabbit login username
    :param rabbit_password: Rabbit login password
    :param prefix: What prefix should the Worker use
    :param persistent: Keep Worker alive and keep on trying forever
    :param consumer_count: How many consumers to use for queues
    :param max_retries: How many times to try to connect
    :return: None
    """
    attack_q = f'cryton_worker.{prefix}.attack.request'
    control_q = f'cryton_worker.{prefix}.control.request'
    queues = (attack_q, control_q)

    worker = Worker(rabbit_host, rabbit_port, rabbit_username, rabbit_password, consumer_count, queues, max_retries,
                    persistent)
    worker.start()

    return None


def install_modules_requirements() -> None:
    """
    Go through module directories and install all requirement files.
    :return: None
    """
    for root, dirs, files in os.walk(config.MODULES_DIR):
        for filename in files:
            if filename == "requirements.txt":
                subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", os.path.join(root, filename)])

    return None

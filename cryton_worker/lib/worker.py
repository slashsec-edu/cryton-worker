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
from multiprocessing import Process, Event
import time


class ThreadConsumer:
    def __init__(self, callback: exec, message: amqpstorm.Message):
        """
        Consumer.
        :param callback: Custom Rabbit callback.
        :param message: RabbitMQ Message.
        """
        self.callback = callback
        self.message = message
        self.correlation_id = self.message.correlation_id
        self._stopped = False

    def __call__(self):
        """
        Rabbit callback for executing custom callbacks and sending response to reply_to.
        :return: None
        """
        self.message.ack()

        logger.logger.debug('Consuming callback.', callback=self.callback, message=self.message)

        message_body = json.loads(self.message.body)
        ret = self.callback(message_body)
        ret = json.dumps(ret)

        self.message.channel.queue.declare(self.message.reply_to)
        self.message.properties.update({'content_encoding': 'utf-8'})
        self.message.properties.update({'timestamp': datetime.datetime.now()})

        response = amqpstorm.Message.create(self.message.channel, ret, self.message.properties)
        response.publish(self.message.reply_to)

    def stop(self):  # TODO: finish later
        pass


class ProcessConsumer:
    def __init__(self, hostname: str, username: str, password: str, port: int, queue: str, callback_executable: exec,
                 max_retries: int):
        """
        ProcessConsumer
        :param hostname: RabbitMQ server hostname.
        :param username: Username to use when connecting to RabbitMQ.
        :param password: Password to use when connecting to RabbitMQ.
        :param port: RabbitMQ server port.
        :param queue: Rabbit queue, that will be consumed.
        :param callback_executable: Custom Rabbit callback.
        """
        self.hostname = hostname
        self.username = username
        self.password = password
        self.port = port
        self.queue = queue
        self.callback_executable = callback_executable
        self.max_retries = max_retries
        self._connection: amqpstorm.Connection or None = None
        self._consumers = []
        self.stopped = Event()
        logger.logger.debug('ProcessConsumer created.', queue=self.queue, callback=self.callback_executable)

    def start(self):
        """
        Start the Consumers.
        :return: None
        """
        self.stopped.clear()
        if not self._connection or self._connection.is_closed:
            self._create_connection()
        while not self.stopped.is_set():
            try:
                # Check our connection for errors.
                self._connection.check_for_errors()
                if not self._connection.is_open:
                    raise amqpstorm.AMQPConnectionError('connection closed')

                channel = self._connection.channel()
                channel.basic.qos(1)
                channel.queue.declare(self.queue)
                channel.basic.consume(self._create_consumer, self.queue)
                channel.start_consuming()

            except amqpstorm.AMQPError as ex:
                # If an error occurs, re-connect and let update_consumers re-open the channels.
                logger.logger.warning(ex)
                self._stop_consumers()
                self._create_connection()

    def stop(self):
        """
        Stop.
        :return: None
        """
        self._stop_consumers()
        self.stopped.set()
        if self._connection is not None:
            self._connection.close()

    def _stop_consumers(self):
        """
        Stop all consumers.
        :return: None
        """
        while self._consumers:
            consumer: ThreadConsumer = self._consumers.pop()
            consumer.stop()

    def _create_connection(self):
        """
        Create a Rabbit connection.
        :return: None
        """
        attempts = 0
        while True:
            attempts += 1
            if self.stopped.is_set():
                break
            try:
                self._connection = amqpstorm.Connection(self.hostname, self.username, self.password, self.port)
                logger.logger.info('Successfully connected.', hostname=self.hostname, port=self.port, queue=self.queue)
                print('Successfully created connection.')
                break
            except amqpstorm.AMQPError as ex:
                logger.logger.warning(ex)
                if self.max_retries and attempts > self.max_retries:
                    logger.logger.error('max number of retries reached')
                    self.stop()
                    raise Exception('max number of retries reached')
                time.sleep(min(attempts * 2, 30))

    def _create_consumer(self, message: amqpstorm.Message):
        """
        Create ThreadedConsumer for new callback.
        :param message: RabbitMQ Message.
        :return: None
        """
        consumer = ThreadConsumer(self.callback_executable, message)
        self._start_consumer(consumer)
        self._consumers.append(consumer)

    @staticmethod
    def _start_consumer(consumer: ThreadConsumer):
        """
        Start a consumer in new Thread.
        :param consumer: Consumer instance.
        :return: None
        """
        thread = Thread(target=consumer)
        thread.daemon = True
        thread.start()


class Worker:
    def __init__(self, rabbit_host: str, rabbit_port: int, rabbit_username: str, rabbit_password: str, prefix: str,
                 core_count: int, max_retries: int = 3):
        """
        Worker.
        """
        self.hostname = rabbit_host
        self.port = rabbit_port
        self.username = rabbit_username
        self.password = rabbit_password
        self.prefix = prefix
        self.max_retries = max_retries

        if core_count == 0:
            self.core_count = len(os.sched_getaffinity(0))
        else:
            self.core_count = core_count

        self._consumers = []
        self._processes = []
        self._stopped = False
        logger.logger.debug('Worker created.', hostname=self.hostname, port=self.port, prefix=self.prefix,
                            core_count=self.core_count)

    def start(self, queues: dict):
        """
        Check consumer condition, create queues and their consumers in processes.
        :param queues: Rabbit queues (without prefix) with callbacks (queue_name: queue_callback)
        :return: None
        """
        # Prepare processes for each queue
        for queue, callback in queues.items():
            queue_with_prefix = queue.format(self.prefix)
            self._create_processes_for_queue(queue_with_prefix, callback)

        logger.logger.info('Worker is running, waiting for connections...', hostname=self.hostname, port=self.port,
                           prefix=self.prefix)
        print('Worker is running, waiting for connections...')

        # Start prepared processes
        for process in self._processes:
            process.start()

        # Keep Worker alive
        while not self._stopped:
            all_stopped = True
            for consumer in self._consumers:
                if not consumer.stopped.is_set():
                    all_stopped = False

            if all_stopped:
                self.stop()
            else:
                time.sleep(5)

    def stop(self):
        """
        Stop Worker and it's consumers.
        :return: None
        """
        while self._consumers:
            consumer: ProcessConsumer = self._consumers.pop()
            consumer.stop()
        self._stopped = True

    def _create_processes_for_queue(self, queue: str, callback: exec):
        """
        Create ScalableConsumers for number of cores and create their processes.
        :param queue: Rabbit queue, that will be consumed.
        :param callback: Custom Rabbit callback.
        :return: None
        """
        for _ in range(self.core_count):
            consumer = ProcessConsumer(self.hostname, self.username, self.password, self.port, queue, callback,
                                       self.max_retries)
            self._consumers.append(consumer)
            self._processes.append(Process(target=consumer.start))


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
    Callback function for controlling Worker.
    :param message_body: RabbitMQ Message body.
    :return: Response containing details about the job.
    """
    event_t = message_body.pop('event_t')
    event_v = event.process_event(event_t, message_body)
    ret = {'event_t': event_t, 'event_v': event_v}

    return ret


def start(rabbit_host: str, rabbit_port: int, rabbit_username: str, rabbit_password: str, prefix: str, core_count: int,
          max_retries: int):
    """
    Creates Worker which connects to Rabbit server and listens for new messages.
    :return: None
    """
    attack_q = 'cryton_worker.{}.attack.request'
    control_q = 'cryton_worker.{}.control.request'

    queues = {attack_q: callback_attack, control_q: callback_control}

    worker = Worker(rabbit_host, rabbit_port, rabbit_username, rabbit_password, prefix, core_count, max_retries)
    worker.start(queues)


def install_modules_requirements():
    """
    Go through module directories and install all requirement files.
    :return: None
    """
    for root, dirs, files in os.walk(config.MODULES_DIR):
        for filename in files:
            if filename == "requirements.txt":
                subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", os.path.join(root, filename)])

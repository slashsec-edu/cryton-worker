from unittest import TestCase
from mock import patch, Mock

from cryton_worker.lib import worker, event, util
import amqpstorm
import subprocess
import time


class TestWorkerFunctions(TestCase):

    @patch('cryton_worker.lib.util.execute_module', Mock())
    @patch('json.dumps')
    @patch('json.loads')
    def test_callback_action(self, mock_loads, mock_dumps):
        mock_loads.return_value = {"test": "test"}
        mock_dumps.return_value = {"test": "test"}
        mock_msg = Mock()
        mock_util = util
        mock_util.execute_module = Mock()

        worker.callback_attack(mock_msg)
        mock_util.execute_module.assert_called()

    @patch('cryton_worker.lib.event.process_event', Mock())
    @patch('json.dumps')
    @patch('json.loads')
    def test_callback_control(self, mock_loads, mock_dumps):
        mock_loads.return_value = {"test": "test"}
        mock_dumps.return_value = {"test": "test"}
        mock_msg = Mock()
        mock_event = event
        mock_event.process_event = Mock()

        worker.callback_control(mock_msg)
        mock_event.process_event.assert_called_once()

    @patch('cryton_worker.lib.worker.install_modules_requirements', Mock())
    @patch('cryton_worker.lib.worker.Worker')
    def test_start(self, mock_worker):
        mock_worker.side_effect = Mock()

        worker.start('', 1, '', '', '', 1, 1)
        mock_worker.assert_called_once()

    @patch('cryton_worker.lib.worker.os.walk')
    def test_install_modules_requirements(self, mock_walk):
        mock_subprocess = subprocess
        mock_subprocess.check_call = Mock()
        mock_walk.return_value = [('.', '.', ['requirements.txt'])]

        worker.install_modules_requirements()
        mock_subprocess.check_call.assert_called_once()


class TestThreadConsumer(TestCase):
    def setUp(self):
        self.custom_callback = Mock()
        self.custom_message = Mock()
        self.consumer = worker.ThreadConsumer(self.custom_callback, self.custom_message)

    @patch('json.dumps', Mock())
    @patch('json.loads', Mock())
    def test_call(self):
        mock_amqpstorm = amqpstorm
        mock_amqpstorm.Message.create = Mock()

        self.consumer()
        self.custom_message.ack.assert_called_once()
        self.custom_callback.assert_called_once()
        mock_amqpstorm.Message.create.assert_called_once()

    def test_stop(self):
        self.consumer.stop()


class TestProcessConsumer(TestCase):
    def setUp(self):
        self.custom_queue = 'test'
        self.custom_callback = Mock()
        self.consumer = worker.ProcessConsumer('test', 'test', 'test', 1, self.custom_queue, self.custom_callback, 1)

    @patch('cryton_worker.lib.worker.ProcessConsumer._create_connection', Mock())
    def test_start(self):
        self.consumer._connection = Mock()
        self.consumer.stopped.is_set = Mock(side_effect=[False, True])
        mock_channel = Mock()
        self.consumer._connection.channel.return_value = mock_channel

        self.consumer.start()
        mock_channel.start_consuming.assert_called_once()

    @patch('cryton_worker.lib.worker.ProcessConsumer._create_connection', Mock())
    @patch('cryton_worker.lib.worker.ProcessConsumer._stop_consumers', Mock())
    def test_start_conn_err(self):
        self.consumer._connection = Mock()
        self.consumer.stopped.is_set = Mock(side_effect=[False, True])
        self.consumer._connection = Mock()
        self.consumer._connection.is_open = False
        mock_logger = worker.logger
        mock_logger.logger = Mock()

        self.consumer.start()
        mock_logger.logger.warning.assert_called_once()

    @patch('cryton_worker.lib.worker.ProcessConsumer._create_connection', Mock())
    def test_start_amqp_err(self):
        def raise_err():
            raise amqpstorm.AMQPError

        self.consumer._connection = Mock()
        self.consumer.stopped.is_set = Mock(side_effect=[False, True])

        mock_channel = Mock()
        self.consumer._connection.channel.return_value = mock_channel
        mock_channel.basic.side_effect = raise_err
        mock_channel.start_consuming.side_effect = raise_err
        self.consumer.start()

    def test_stop(self):
        mock_stop = Mock()
        self.consumer._stop_consumers = mock_stop
        mock_stopped = Mock()
        self.consumer.stopped = mock_stopped
        mock_conn = Mock()
        self.consumer._connection = mock_conn

        self.consumer.stop()
        mock_stop.assert_called_once()
        mock_stopped.set.assert_called_once()
        mock_conn.close.assert_called_once()

    def test__stop_consumers(self):
        mock_thread_consumer = Mock()
        self.consumer._consumers = [mock_thread_consumer]

        self.consumer._stop_consumers()
        self.assertEqual([], self.consumer._consumers)
        mock_thread_consumer.stop.assert_called_once()

    def test__create_connection(self):
        mock_amqpstorm = amqpstorm
        mock_amqpstorm.Connection = Mock()

        self.consumer._create_connection()
        mock_amqpstorm.Connection.assert_called_once()

    def test__create_connection_stopped(self):
        self.consumer.stopped.is_set = Mock(return_value=True)

        self.consumer._create_connection()
        self.consumer.stopped.is_set.assert_called_once()

    def test__create_connection_err(self):
        def raise_err(*_):
            raise amqpstorm.AMQPError

        self.consumer.max_retries = 1
        mock_time = time
        mock_time.sleep = Mock()
        mock_amqpstorm = amqpstorm
        mock_amqpstorm.Connection = Mock(side_effect=raise_err)

        with self.assertRaises(Exception):
            self.consumer._create_connection()

    @patch('cryton_worker.lib.worker.ProcessConsumer._start_consumer', Mock())
    def test__create_consumer(self):
        mock_worker = worker
        mock_worker.ThreadConsumer = Mock()
        self.consumer._create_consumer(Mock())
        self.assertNotEqual([], self.consumer._consumers)

    def test__start_consumer(self):
        mock_thread = worker.Thread
        mock_thread.start = Mock()
        self.consumer._start_consumer(Mock())
        mock_thread.start.assert_called_once()


class TestWorker(TestCase):
    def setUp(self):
        self.custom_queue = 'test'
        self.custom_callback = Mock()
        self.worker = worker.Worker('', 1, '', '', '', 1)

    def test_init_with_custom_cores(self):
        self.worker = worker.Worker('', 1, '', '', '', 1)

    @patch('cryton_worker.lib.worker.Worker._create_processes_for_queue', Mock())
    def test_start(self):
        mock_time = time
        mock_time.sleep = Mock()
        queues = {self.custom_queue: self.custom_callback}
        self.worker._processes = [Mock()]
        self.worker._stopped = Mock(side_effect=[False, True])

        self.worker.start(queues)

    def test_stop(self):
        mock_consumer = Mock()
        self.worker._consumers = [mock_consumer]
        self.worker.stop()

        mock_consumer.stop.assert_called_once()

    @patch('cryton_worker.lib.worker.ProcessConsumer', Mock())
    @patch('cryton_worker.lib.worker.Process', Mock())
    def test__create_processes_for_queue(self):
        self.worker._create_processes_for_queue(self.custom_queue, self.custom_callback)
        self.assertNotEqual([], self.worker._consumers)
        self.assertNotEqual([], self.worker._processes)

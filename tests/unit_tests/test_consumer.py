from unittest import TestCase
from mock import patch, Mock

from cryton_worker.lib import consumer
from cryton_worker.lib.util import logger
import amqpstorm


@patch("cryton_worker.lib.util.logger.logger", logger.structlog.getLogger("cryton-worker-debug"))
class TestConsumer(TestCase):
    def setUp(self):
        self.mock_main_queue = Mock()
        self.consumer_obj = consumer.Consumer(self.mock_main_queue, "host", 1, "user", "pass", "prefix", 3, 3, False)
        self.consumer_obj._main_queue = Mock()

    def test_init_wrong_consumers(self):
        consumer_obj = consumer.Consumer(self.mock_main_queue, "host", 1, "user", "pass", "prefix", 0, 3, False)
        self.assertEqual(consumer_obj._consumer_count, 1)

    def test___str__(self):
        result = str(self.consumer_obj)
        self.assertEqual(result, "user@host:1")

    @patch("cryton_worker.lib.consumer.Consumer._update_connection", Mock())
    @patch("cryton_worker.lib.consumer.Consumer._start_threaded_consumers", Mock())
    @patch("cryton_worker.lib.worker.time.sleep")
    def test_start(self, mock_sleep):
        mock_sleep.side_effect = amqpstorm.AMQPConnectionError
        self.consumer_obj.start()

    @patch("cryton_worker.lib.consumer.Consumer._update_connection")
    @patch("cryton_worker.lib.consumer.Consumer._start_threaded_consumers", Mock())
    @patch("cryton_worker.lib.worker.time.sleep")
    def test_start_persistent(self, mock_sleep, mock_update_connection):
        mock_update_connection.side_effect = [False, RuntimeError]
        mock_sleep.side_effect = amqpstorm.AMQPConnectionError
        self.consumer_obj._persistent = True
        with self.assertLogs("cryton-worker-debug", level="DEBUG") as cm:
            with self.assertRaises(RuntimeError):
                self.consumer_obj.start()
        self.assertIn("Ignoring connection error due to persistent mode.", cm.output[1])

    def test_stop(self):
        mock_task = Mock()
        mock_task.join.side_effect = KeyboardInterrupt
        mock_connection, mock_channel = Mock(), Mock()
        mock_connection.channels = {1: mock_channel}

        self.consumer_obj._connection = mock_connection
        self.consumer_obj._tasks.append(Mock())
        self.consumer_obj._tasks.append(mock_task)

        self.consumer_obj.stop()
        mock_task.join.assert_called_once()
        mock_task.kill.assert_called_once()
        mock_connection.close.assert_called_once()
        mock_channel.close.assert_called_once()

    @patch("cryton_worker.lib.consumer.Consumer._create_connection")
    def test__update_connection_is_none(self, mock_create_conn: Mock):
        result = self.consumer_obj._update_connection()
        self.assertTrue(result)
        mock_create_conn.assert_called_once()

    def test__update_connection_is_ok(self):
        self.consumer_obj._connection = Mock()
        self.consumer_obj._connection.is_open = True
        result = self.consumer_obj._update_connection()
        self.assertFalse(result)

    @patch("cryton_worker.lib.consumer.Consumer._create_connection", Mock())
    def test__update_connection_is_closed(self):
        self.consumer_obj._connection = Mock()
        self.consumer_obj._connection.is_open = False
        result = self.consumer_obj._update_connection()
        self.assertTrue(result)

    @patch("threading.Thread", Mock())
    @patch("threading.Thread.start")
    def test__start_threaded_consumers(self, mock_start):
        self.consumer_obj._start_threaded_consumers()
        mock_start.assert_called()

    def test__threaded_consumer(self):
        mock_connection, mock_channel = Mock(), Mock()
        mock_connection.channel.return_value = mock_channel
        self.consumer_obj._connection = mock_connection
        self.consumer_obj._threaded_consumer(1)
        mock_channel.start_consuming.assert_called()

    def test__threaded_consumer_error(self):
        with self.assertLogs("cryton-worker-debug", level="DEBUG") as cm:
            mock_connection = Mock()
            mock_connection.channel.side_effect = amqpstorm.AMQPError
            self.consumer_obj._connection = mock_connection
            self.consumer_obj._threaded_consumer(1)
        self.assertIn("Threaded consumer encountered an error.", cm.output[1])

    @patch("cryton_worker.lib.task.AttackTask")
    def test__callback_attack(self, mock_task):
        self.consumer_obj._callback_attack(Mock())
        self.assertNotEqual([], self.consumer_obj._tasks)
        mock_task.return_value.start.assert_called()

    @patch("cryton_worker.lib.task.ControlTask")
    def test__callback_control(self, mock_task):
        self.consumer_obj._callback_control(Mock())
        self.assertNotEqual([], self.consumer_obj._tasks)
        mock_task.return_value.start.assert_called()

    @patch("time.sleep", Mock())
    @patch("amqpstorm.Connection")
    def test__create_connection(self, mock_conn: Mock):
        self.consumer_obj._create_connection()
        mock_conn.assert_called_once()
        mock_conn.side_effect = amqpstorm.AMQPError
        with self.assertRaises(amqpstorm.AMQPConnectionError):
            self.consumer_obj._create_connection()

    def test__create_connection_stopped(self):
        self.consumer_obj.stopped = True
        self.assertIsNone(self.consumer_obj._create_connection())

    @patch("amqpstorm.Message.create")
    def test_send_message(self, mock_create):
        mock_connection, mock_channel = Mock(), Mock()
        mock_connection.channel.return_value = mock_channel
        self.consumer_obj._connection = mock_connection
        self.consumer_obj.send_message("", {}, {})
        mock_create.assert_called_once()

    def test_pop_task(self):
        mock_task = Mock()
        mock_task.correlation_id = "id"
        self.consumer_obj._tasks.append(mock_task)
        result = self.consumer_obj.pop_task("id")
        self.assertEqual(result, mock_task)

    def test_pop_task_not_found(self):
        self.assertIsNone(self.consumer_obj.pop_task("id"))

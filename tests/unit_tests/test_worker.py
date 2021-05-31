from unittest import TestCase
from mock import patch, Mock

from cryton_worker.lib import worker
from cryton_worker.lib.util import constants as co, logger, util


@patch("cryton_worker.lib.util.logger.logger", logger.structlog.getLogger("cryton-worker-debug"))
class TestWorker(TestCase):
    def setUp(self):
        self.mock_main_queue = Mock()
        self.worker_obj = worker.Worker("host", 1, "user", "pass", "prefix", 3, 3, 3, False)
        self.worker_obj._main_queue = self.mock_main_queue

    def test_init_wrong_consumers(self):
        worker_obj = worker.Worker("host", 1, "user", "pass", "prefix", 3, 0, 3, False)
        self.assertEqual(worker_obj._processor_count, 1)

    @patch("cryton_worker.lib.worker.Worker._start_consumer", Mock())
    @patch("cryton_worker.lib.worker.Worker._start_threaded_processors", Mock())
    @patch("cryton_worker.lib.worker.Worker.stop")
    @patch("cryton_worker.lib.worker.time.sleep")
    def test_start(self, mock_sleep, mock_stop):
        mock_sleep.side_effect = KeyboardInterrupt
        self.worker_obj.start()
        mock_stop.assert_called_once()

    @patch("cryton_worker.lib.worker.Worker._stop_threaded_processors", Mock())
    @patch("cryton_worker.lib.worker.Worker._stop_triggers", Mock())
    @patch("cryton_worker.lib.consumer.Consumer.stop", Mock())
    def test_stop(self):
        self.worker_obj.stop()
        self.assertTrue(self.worker_obj._stopped)

    @patch("threading.Thread", Mock())
    @patch("threading.Thread.start")
    def test__start_threaded_processors(self, mock_start):
        self.worker_obj._start_threaded_processors()
        mock_start.assert_called()

    def test__stop_threaded_processors(self):
        self.worker_obj._stop_threaded_processors()
        self.mock_main_queue.put.assert_called()

    @patch("threading.Thread", Mock())
    @patch("threading.Thread.start")
    def test__start_consumer(self, mock_start):
        self.worker_obj._start_consumer()
        mock_start.assert_called()

    def test__stop_triggers(self):
        mock_trigger_obj = Mock()
        self.worker_obj._triggers.append(mock_trigger_obj)
        self.worker_obj._stop_triggers()
        mock_trigger_obj.stop.assert_called_once()

    def test__threaded_processor_action_shutdown(self):
        self.mock_main_queue.get.return_value = util.PrioritizedItem(0,
                                                                     {co.ACTION: co.ACTION_SHUTDOWN_THREADED_PROCESSOR})
        self.worker_obj._threaded_processor(1)

    def test__threaded_processor_action_unknown(self):
        self.mock_main_queue.get.return_value = util.PrioritizedItem(0, {co.ACTION: "UNKNOWN"})
        with self.assertLogs("cryton-worker-debug", level="WARNING") as cm:
            with self.assertRaises(KeyError):
                self.worker_obj._threaded_processor(1)
        self.assertIn("Request contains unknown action.", cm.output[0])

    @patch("cryton_worker.lib.worker.Worker._stop_threaded_processors")
    def test__threaded_processor_action_exception(self, mock_action):
        mock_action.side_effect = RuntimeError
        self.mock_main_queue.get.return_value = util.PrioritizedItem(0, {co.ACTION: co.ACTION_SEND_MESSAGE})
        with self.assertLogs("cryton-worker-debug", level="WARNING") as cm:
            with self.assertRaises(KeyError):
                self.worker_obj._threaded_processor(1)
        self.assertIn("Request threw an exception in the process.", cm.output[0])

    @patch("cryton_worker.lib.consumer.Consumer.pop_task", Mock())
    def test__kill_task(self):
        mock_pipe = Mock()
        self.worker_obj._kill_task({co.RESULT_PIPE: mock_pipe, co.CORRELATION_ID: "1"})
        mock_pipe.send.assert_called_once_with({co.RETURN_CODE: co.CODE_OK})

    @patch("cryton_worker.lib.consumer.Consumer.pop_task")
    def test__kill_task_error(self, mock_pop_task):
        mock_task = Mock()
        mock_task.kill.side_effect = RuntimeError
        mock_pop_task.return_value = mock_task
        mock_pipe = Mock()
        self.worker_obj._kill_task({co.RESULT_PIPE: mock_pipe, co.CORRELATION_ID: "1"})
        mock_pipe.send.assert_called_once_with({co.RETURN_CODE: co.CODE_ERROR, co.STD_ERR: ""})

    @patch("cryton_worker.lib.consumer.Consumer.pop_task")
    def test__kill_task_not_found(self, mock_pop_task):
        mock_pop_task.return_value = None
        mock_pipe = Mock()
        self.worker_obj._kill_task({co.RESULT_PIPE: mock_pipe, co.CORRELATION_ID: "1"})
        mock_pipe.send.assert_called_once_with({co.RETURN_CODE: co.CODE_ERROR, co.STD_ERR: "Couldn't find the Task."})

    @patch("cryton_worker.lib.consumer.Consumer.pop_task")
    def test__finish_task(self, mock_pop_task):
        self.worker_obj._finish_task({co.CORRELATION_ID: "1", co.DATA: ""})
        mock_pop_task.assert_called_once()

    @patch("cryton_worker.lib.consumer.Consumer.send_message")
    def test__send_message(self, mock_send_message):
        self.worker_obj._send_message({co.QUEUE_NAME: "", co.DATA: "", co.PROPERTIES: {}})
        mock_send_message.assert_called_once()

    @patch("cryton_worker.lib.triggers.HTTPTrigger.add_activator", Mock())
    def test__start_trigger_new(self):
        mock_pipe = Mock()
        self.worker_obj._start_trigger({co.RESULT_PIPE: mock_pipe,
                                        co.DATA: {co.T_HOST: "", co.T_PORT: "", co.T_TYPE: "HTTP"}})
        mock_pipe.send.assert_called_once_with({co.RETURN_CODE: co.CODE_OK})

    @patch("cryton_worker.lib.triggers.HTTPTrigger.add_activator", Mock())
    def test__start_trigger_existing(self):
        mock_trigger_obj = Mock()
        mock_trigger_obj.compare_identifiers.return_value = True
        mock_pipe = Mock()
        self.worker_obj._triggers.append(mock_trigger_obj)
        self.worker_obj._start_trigger(
            {co.RESULT_PIPE: mock_pipe, co.DATA: {co.T_HOST: "", co.T_PORT: "", co.T_TYPE: "HTTP"}})
        mock_pipe.send.assert_called_once_with({co.RETURN_CODE: co.CODE_OK})

    @patch("cryton_worker.lib.triggers.HTTPTrigger.add_activator")
    def test__start_trigger_error(self, mock_add_activator):
        mock_add_activator.side_effect = RuntimeError
        mock_pipe = Mock()
        self.worker_obj._start_trigger(
            {co.RESULT_PIPE: mock_pipe, co.DATA: {co.T_HOST: "", co.T_PORT: "", co.T_TYPE: "HTTP"}})
        mock_pipe.send.assert_called_once_with({co.RETURN_CODE: co.CODE_ERROR, co.STD_ERR: ""})

    def test__stop_trigger_exists(self):
        mock_trigger_obj = Mock()
        mock_trigger_obj.compare_identifiers.return_value = True
        mock_trigger_obj.any_activator_exists.return_value = False
        mock_trigger_obj.remove_activator.return_value = None
        mock_pipe = Mock()
        self.worker_obj._triggers.append(mock_trigger_obj)
        self.worker_obj._stop_trigger({co.RESULT_PIPE: mock_pipe,
                                       co.DATA: {co.T_HOST: "", co.T_PORT: "", co.T_TYPE: "HTTP"}})
        mock_pipe.send.assert_called_once_with({co.RETURN_CODE: co.CODE_OK})

    def test__stop_trigger_exists_error(self):
        mock_trigger_obj = Mock()
        mock_trigger_obj.compare_identifiers.return_value = True
        mock_trigger_obj.remove_activator.side_effect = RuntimeError
        mock_pipe = Mock()
        self.worker_obj._triggers.append(mock_trigger_obj)
        self.worker_obj._stop_trigger({co.RESULT_PIPE: mock_pipe,
                                       co.DATA: {co.T_HOST: "", co.T_PORT: "", co.T_TYPE: "HTTP"}})
        mock_pipe.send.assert_called_once_with({co.RETURN_CODE: co.CODE_ERROR, co.STD_ERR: ""})

    def test__stop_trigger_not_found(self):
        mock_pipe = Mock()
        self.worker_obj._stop_trigger({co.RESULT_PIPE: mock_pipe,
                                       co.DATA: {co.T_HOST: "", co.T_PORT: "", co.T_TYPE: "HTTP"}})
        mock_pipe.send.assert_called_once_with({co.RETURN_CODE: co.CODE_ERROR, co.STD_ERR: "Trigger not found."})

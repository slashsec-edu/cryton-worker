from unittest import TestCase
from mock import patch, Mock

from cryton_worker.lib import worker, util
import amqpstorm
import subprocess


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

    @patch('cryton_worker.lib.event.kill_execution', Mock(return_value={'return_code': 0}))
    @patch('cryton_worker.lib.event.validate_module', Mock(return_value={'return_code': 0}))
    @patch('cryton_worker.lib.event.list_modules', Mock(return_value={'return_code': 0}))
    @patch('cryton_worker.lib.event.list_sessions', Mock(return_value={'return_code': 0}))
    @patch('cryton_worker.lib.event.health_check', Mock(return_value={'return_code': 0}))
    def test_callback_control(self):
        ret = worker.callback_control({'event_t': 'KILL_EXECUTION'})
        self.assertEqual(ret.get('event_v'), {'return_code': 0})

        ret = worker.callback_control({'event_t': 'VALIDATE_MODULE'})
        self.assertEqual(ret.get('event_v'), {'return_code': 0})

        ret = worker.callback_control({'event_t': 'LIST_MODULES'})
        self.assertEqual(ret.get('event_v'), {'return_code': 0})

        ret = worker.callback_control({'event_t': 'LIST_SESSIONS'})
        self.assertEqual(ret.get('event_v'), {'return_code': 0})

        ret = worker.callback_control({'event_t': 'HEALTHCHECK'})
        self.assertEqual(ret.get('event_v'), {'return_code': 0})

        ret = worker.callback_control({'event_t': 'UNKNOWN'})
        self.assertEqual(ret.get('event_v'), {'return_code': -2})

    @patch('cryton_worker.lib.worker.install_modules_requirements', Mock())
    @patch('cryton_worker.lib.worker.Worker')
    def test_start(self, mock_worker):
        mock_worker.side_effect = Mock()

        worker.start('', 1, '', '', '', 1, 1, False)
        mock_worker.assert_called_once()

    @patch('cryton_worker.lib.worker.os.walk')
    def test_install_modules_requirements(self, mock_walk):
        mock_subprocess = subprocess
        mock_subprocess.check_call = Mock()
        mock_walk.return_value = [('.', '.', ['requirements.txt'])]

        worker.install_modules_requirements()
        mock_subprocess.check_call.assert_called_once()


class TestTask(TestCase):
    def setUp(self):
        self.channel = Mock()
        self.msg_body = '{"var": "val"}'
        self.request_queue = Mock()
        self.task = worker.Task(amqpstorm.message.Message.create(self.channel, self.msg_body),
                                self.request_queue)

    @patch('cryton_worker.lib.worker.amqpstorm.message.Message.ack', Mock())
    def test__call__(self):
        self.assertIsNone(self.task())

    @patch('cryton_worker.lib.worker.callback_attack')
    @patch('cryton_worker.lib.worker.callback_control')
    def test__decide_callback(self, mock_control: Mock, mock_attack: Mock):
        mock_attack.return_value = {'test': 'test'}
        ret = self.task._decide_callback({'attack_module': 'test'})
        mock_attack.assert_called_once()
        self.assertEqual(ret, {'test': 'test'})

        mock_control.return_value = {'test': 'test'}
        ret = self.task._decide_callback({'event_t': 'test'})
        mock_control.assert_called_once()
        self.assertEqual(ret, {'test': 'test'})

        ret = self.task._decide_callback({})
        self.assertEqual(ret, {'err': 'Unknown request, \'attack_module\' or \'event_t\' must be defined.'})

    @patch('amqpstorm.Message.create')
    def test_send_response(self, mock_create):
        self.task.send_response('test')
        mock_create.assert_called_once()


class TestWorker(TestCase):
    def setUp(self):
        self.custom_queue = 'test'
        self.custom_callback = Mock()
        self.worker = worker.Worker('', 1, '', '', 1, ('q1', 'q2'))
        self.worker.req_queue = Mock()

    def test_init_with_zero_consumers(self):
        worker_obj = worker.Worker('', 1, '', '', 0, ('q1', 'q2'))
        self.assertIsInstance(worker_obj, worker.Worker)
        self.assertEqual(worker_obj.consumer_count, 1)

    @patch('cryton_worker.lib.worker.Worker._update_connection', Mock(return_value=True))
    @patch('cryton_worker.lib.worker.Worker._update_consumers', Mock())
    @patch('cryton_worker.lib.worker.Worker._process_pipe')
    def test_start_keyboard_interrupt(self, mock_pipe: Mock):
        mock_pipe.side_effect = KeyboardInterrupt

        self.worker.start()

    @patch('cryton_worker.lib.worker.Worker._update_connection', Mock(return_value=True))
    @patch('cryton_worker.lib.worker.Worker._update_consumers', Mock())
    @patch('cryton_worker.lib.worker.Worker._process_pipe')
    def test_start_conn_err(self, mock_pipe: Mock):
        mock_pipe.side_effect = amqpstorm.AMQPConnectionError

        self.worker.start()

    @patch('cryton_worker.lib.worker.Worker._create_connection')
    def test__update_connection(self, mock_create_conn: Mock):
        ret = self.worker._update_connection()
        self.assertTrue(ret)
        mock_create_conn.assert_called_once()

        self.worker._connection = Mock()
        self.worker._connection.is_open = True
        ret = self.worker._update_connection()
        self.assertFalse(ret)

        self.worker._connection = Mock()
        self.worker._connection.is_open = False
        ret = self.worker._update_connection()
        self.assertTrue(ret)

    @patch('threading.Thread', Mock())
    @patch('threading.Thread.start')
    def test__update_consumers(self, mock_start: Mock):
        self.worker._update_consumers()

        mock_start.assert_called()

    @patch('cryton_worker.lib.worker.Worker._kill')
    def test__process_pipe_kill(self, mock_kill: Mock):
        mock_kill.return_value = (0, '')
        mock_pipe = Mock()
        self.worker.req_queue.get.return_value = ('KILL', mock_pipe, '1')

        self.worker._process_pipe()

        mock_pipe.send.assert_called_once_with((0, ''))

    def test__process_pipe_free(self):
        mock_task, mock_task_process = Mock(), Mock()
        mock_task.correlation_id = '1'
        self.worker._tasks.update({mock_task: mock_task_process})
        self.worker.req_queue.get.return_value = ('FREE', mock_task.correlation_id, '')

        self.worker._process_pipe()

        self.assertEqual(self.worker._tasks, {})

    def test__process_pipe_errors(self):
        self.worker.req_queue.get.return_value = ('UNKNOWN',)
        self.worker._process_pipe()

        self.worker.req_queue.get.side_effect = Exception
        self.worker._process_pipe()

    def test_consumer(self):
        mock_connection, mock_channel = Mock(), Mock()
        mock_connection.channel.return_value = mock_channel
        self.worker._connection = mock_connection

        self.worker.consumer()

        mock_channel.start_consuming.assert_called()

    @patch('cryton_worker.lib.worker.Task', Mock())
    @patch('multiprocessing.Process', Mock())
    @patch('multiprocessing.Process.start')
    def test__process_callback(self, mock_start: Mock):
        msg = amqpstorm.message.Message.create(Mock(), Mock())

        self.worker._process_callback(msg)

        mock_start.assert_called_once()

    def test_stop(self):
        mock_task, mock_task_process = Mock(), Mock()
        mock_connection, mock_channel = Mock(), Mock()
        mock_connection.channels = {1: mock_channel}
        self.worker._connection = mock_connection
        self.worker._tasks.update({mock_task: mock_task_process})

        self.worker.stop()

        mock_task_process.join.assert_called_once()
        mock_connection.close.assert_called_once()
        mock_channel.close.assert_called_once()

    def test_stop_keyboard_interrupt(self):
        mock_task1, mock_task_process1 = Mock(), Mock()
        mock_task2, mock_task_process2 = Mock(), Mock()
        mock_task_process1.join.side_effect = KeyboardInterrupt
        mock_task_process2.join.side_effect = KeyboardInterrupt
        mock_connection, mock_channel = Mock(), Mock()
        mock_connection.channels = {1: mock_channel}
        self.worker._connection = mock_connection
        self.worker._tasks.update({mock_task1: mock_task_process1, mock_task2: mock_task_process2})

        self.worker.stop()

        mock_task_process1.kill.assert_called()
        mock_task_process2.kill.assert_called()
        mock_connection.close.assert_called_once()
        mock_channel.close.assert_called_once()

    def test__kill(self):
        mock_task, mock_task_process = Mock(), Mock()
        mock_task.correlation_id = '1'
        self.worker._tasks.update({mock_task: mock_task_process})

        ret = self.worker._kill('1')

        self.assertEqual(ret, (0, ''))
        mock_task_process.kill.assert_called_once()

    def test__kill_err(self):
        mock_task, mock_task_process = Mock(), Mock()
        mock_task_process.kill.side_effect = Exception('ex')
        mock_task.correlation_id = '1'
        self.worker._tasks.update({mock_task: mock_task_process})

        ret = self.worker._kill('1')

        self.assertEqual(ret, (-2, 'ex'))
        mock_task_process.kill.assert_called_once()

    def test__kill_not_found(self):
        ret = self.worker._kill('1')
        self.assertEqual(ret, (-1, 'not found'))

    @patch('time.sleep', Mock())
    @patch('amqpstorm.Connection')
    def test__create_connection(self, mock_conn: Mock):
        self.worker._create_connection()
        mock_conn.assert_called_once()

        mock_conn.side_effect = amqpstorm.AMQPError

        with self.assertRaises(amqpstorm.AMQPConnectionError):
            self.worker._create_connection()

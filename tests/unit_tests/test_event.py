from unittest import TestCase
from mock import patch, Mock

from cryton_worker.lib import event


class TestEvent(TestCase):

    def test_process_event(self):
        ret = event.process_event('test', {'test': 'test'})
        self.assertEqual({'return_code': -2}, ret)

    @patch('cryton_worker.lib.event.event_kill_execution', return_value={'return_code': 0})
    def test_process_event_kill(self, mock_event):
        ret = event.process_event('KILL_EXECUTION', {'test': 'test'})
        self.assertEqual({'return_code': 0}, ret)

    @patch('cryton_worker.lib.event.event_validate_module', return_value={'return_code': 0})
    def test_process_event_validate(self, mock_event):
        ret = event.process_event('VALIDATE_MODULE', {'test': 'test'})
        self.assertEqual({'return_code': 0}, ret)

    @patch('cryton_worker.lib.event.event_list_modules', return_value={'return_code': 0})
    def test_process_event_list_mod(self, mock_event):
        ret = event.process_event('LIST_MODULES', {'test': 'test'})
        self.assertEqual({'return_code': 0}, ret)

    @patch('cryton_worker.lib.event.event_list_sessions', return_value={'return_code': 0})
    def test_process_event_list_sess(self, mock_event):
        ret = event.process_event('LIST_SESSIONS', {'test': 'test'})
        self.assertEqual({'return_code': 0}, ret)

    @patch('cryton_worker.lib.event.event_health_check', return_value={'return_code': 0})
    def test_process_event_list_sess(self, mock_event):
        ret = event.process_event('HEALTHCHECK', {'test': 'test'})
        self.assertEqual({'return_code': 0}, ret)

    @patch('cryton_worker.lib.util.validate_module')
    def test_event_validate_module(self, mock_util):
        mock_util.return_value = {'return_code': 0}
        ret = event.event_validate_module({'test': 'test'})
        self.assertEqual({'return_code': 0}, ret)

    @patch('cryton_worker.lib.util.list_modules')
    def test_event_list_modules(self, mock_util):
        mock_util.return_value = 0
        ret = event.event_list_modules({'test': 'test'})
        self.assertEqual({'module_list': 0}, ret)

    @patch('cryton_worker.lib.util.list_sessions')
    def test_event_list_sessions(self, mock_util):
        mock_util.return_value = 0
        ret = event.event_list_sessions({'test': 'test'})
        self.assertEqual({'session_list': 0}, ret)

    @patch('cryton_worker.lib.util.kill_execution')
    def test_event_kill_execution(self, mock_util):
        mock_util.return_value = 0
        ret = event.event_kill_execution({'test': 'test'})
        self.assertEqual({'return_code': 0}, ret)

    def test_event_health_check(self):
        ret = event.event_health_check({'test': 'test'})
        self.assertEqual({'return_code': 0}, ret)

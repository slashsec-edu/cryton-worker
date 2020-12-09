from unittest import TestCase
from mock import patch, Mock

from cryton_worker.lib import event


class TestEvent(TestCase):
    @patch('cryton_worker.lib.util.validate_module')
    def test_validate_module(self, mock_util):
        mock_util.return_value = {'return_code': 0}
        ret = event.validate_module({'test': 'test'})
        self.assertEqual({'return_code': 0}, ret)

    @patch('cryton_worker.lib.util.list_modules')
    def test_list_modules(self, mock_util):
        mock_util.return_value = 0
        ret = event.list_modules({'test': 'test'})
        self.assertEqual({'module_list': 0}, ret)

    @patch('cryton_worker.lib.util.list_sessions')
    def test_list_sessions(self, mock_util):
        mock_util.return_value = 0
        ret = event.list_sessions({'test': 'test'})
        self.assertEqual({'session_list': 0}, ret)

    def test_kill_execution(self):
        mock_pipe = Mock()
        mock_pipe.recv.return_value = (0, '')
        ret = event.kill_execution({'test': 'test', 'request_queue': Mock(), 'response_pipe': mock_pipe})
        self.assertEqual({'return_code': 0, 'std_err': ''}, ret)

    def test_health_check(self):
        ret = event.health_check({'test': 'test'})
        self.assertEqual({'return_code': 0}, ret)

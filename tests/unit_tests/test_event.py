from unittest import TestCase
from mock import patch, Mock

from cryton_worker.lib import event
from cryton_worker.lib.util import constants as co


class TestEvent(TestCase):
    def setUp(self):
        self.mock_main_queue = Mock()
        self.mock__response_pipe = Mock()
        self.mock__request_pipe = Mock()

        with patch("cryton_worker.lib.event.Pipe") as mocked_pipe:
            mocked_pipe.return_value = self.mock__response_pipe, self.mock__request_pipe
            self.event_obj = event.Event({}, self.mock_main_queue)

    @patch("cryton_worker.lib.util.util.validate_module")
    def test_validate_module(self, mock_validate):
        mock_validate.return_value = {co.RETURN_CODE: co.CODE_OK}
        result = self.event_obj.validate_module()
        self.assertEqual({co.RETURN_CODE: co.CODE_OK}, result)

    @patch("cryton_worker.lib.util.util.list_modules")
    def test_list_modules(self, mock_list_modules):
        module_list = ["mod"]
        mock_list_modules.return_value = module_list
        result = self.event_obj.list_modules()
        self.assertEqual({co.MODULE_LIST: module_list}, result)

    @patch("cryton_worker.lib.util.util.Metasploit")
    def test_list_sessions(self, mock_sessions):
        session_list = ["session"]
        mock_sessions.return_value.get_target_sessions.return_value = session_list
        result = self.event_obj.list_sessions()
        self.assertEqual({co.SESSION_LIST: session_list}, result)

    def test_kill_step_execution(self):
        self.mock__response_pipe.recv.return_value = {co.RETURN_CODE: co.CODE_OK}
        result = self.event_obj.kill_step_execution()
        self.assertEqual({co.RETURN_CODE: co.CODE_OK}, result)

    def test_health_check(self):
        result = self.event_obj.health_check()
        self.assertEqual({co.RETURN_CODE: co.CODE_OK}, result)

    def test_start_trigger(self):
        self.mock__response_pipe.recv.return_value = {co.RETURN_CODE: co.CODE_OK}
        result = self.event_obj.start_trigger()
        self.assertEqual({co.RETURN_CODE: co.CODE_OK}, result)

    def test_stop_trigger(self):
        self.mock__response_pipe.recv.return_value = {co.RETURN_CODE: co.CODE_OK}
        result = self.event_obj.stop_trigger()
        self.assertEqual({co.RETURN_CODE: co.CODE_OK}, result)

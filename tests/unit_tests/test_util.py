from unittest import TestCase
from mock import patch, Mock

import os
import subprocess

from cryton_worker.lib.util import util, module_util


class TestUtil(TestCase):
    @patch("cryton_worker.lib.util.util.execute_module")
    def test_run_module(self, execute_module):
        execute_module.return_value = {"return_code": 0, "file": {"file_content": 1}}

        ret = util.run_module("test", {"test": "test"})
        self.assertEqual({"return_code": 0, "file": {"file_content": "MQ==", "file_encoding": "base64"}}, ret)

    @patch("cryton_worker.lib.util.util.import_module")
    def test_execute_module(self, mock_import):
        mock_import.return_value.execute.return_value = {"return_code": 0}

        ret = util.execute_module("test", {"test": "test"})
        self.assertEqual({"return_code": 0}, ret)

    @patch("cryton_worker.lib.util.util.import_module")
    def test_execute_module_import_err(self, mock_import):
        mock_import.side_effect = ModuleNotFoundError

        ret = util.execute_module("test", {"test": "test"})
        self.assertEqual(-2, ret.get("return_code"))

    @patch("cryton_worker.lib.util.util.import_module")
    def test_execute_module_call_err(self, mock_import):
        mock_import.return_value.execute.side_effect = RuntimeError

        ret = util.execute_module("test", {"test": "test"})
        self.assertEqual(-2, ret.get("return_code"))

    @patch("cryton_worker.lib.util.util.import_module")
    def test_execute_module_attribute_err(self, mock_import):
        mock_import.return_value.__delattr__("execute")

        ret = util.execute_module("test", {"test": "test"})
        self.assertEqual(-2, ret.get("return_code"))

    @patch("cryton_worker.lib.util.util.import_module")
    def test_validate_module(self, mock_import):
        mock_import.return_value.validate.return_value = 0

        ret = util.validate_module("test", {"test": "test"})
        self.assertEqual(0, ret.get("return_code"))

    @patch("cryton_worker.lib.util.util.import_module")
    def test_validate_module_import_err(self, mock_import):
        mock_import.side_effect = ModuleNotFoundError

        ret = util.validate_module("test", {"test": "test"})
        self.assertEqual(-2, ret.get("return_code"))

    @patch("cryton_worker.lib.util.util.import_module")
    def test_validate_module_call_err(self, mock_import):
        mock_import.return_value.validate.side_effect = RuntimeError

        ret = util.validate_module("test", {"test": "test"})
        self.assertEqual(-2, ret.get("return_code"))

    @patch("cryton_worker.lib.util.util.import_module")
    def test_validate_module_attribute_err(self, mock_import: Mock):
        mock_import.return_value.__delattr__("validate")

        ret = util.validate_module("test", {"test": "test"})
        self.assertEqual(-2, ret.get("return_code"))

    @patch("importlib.util")
    def test_import_module(self, mock_import):
        util.import_module("test")
        mock_import.module_from_spec.assert_called()

    @patch("importlib.util")
    def test_import_module_missing_module(self, mock_import):
        mock_import.module_from_spec.side_effect = ModuleNotFoundError

        with self.assertRaises(ModuleNotFoundError):
            util.import_module("test")

    @patch("cryton_worker.etc.config.MODULES_DIR", "/tmp/mods4a4a5a7")
    def test_list_modules(self):
        ret = util.list_modules()
        self.assertEqual([], ret)

    @patch("cryton_worker.lib.util.util.os.walk")
    def test_install_modules_requirements(self, mock_walk):
        mock_subprocess = subprocess
        mock_subprocess.check_call = Mock()
        mock_walk.return_value = [(".", ".", ["requirements.txt"])]

        util.install_modules_requirements()
        mock_subprocess.check_call.assert_called_once()

    def test_create_prioritized_item(self):
        item = {}
        priority = 0
        timestamp = 1
        item_obj = util.PrioritizedItem(priority, item, timestamp)
        self.assertEqual((priority, item, timestamp), (item_obj.priority, item_obj.item, item_obj.timestamp))

    def test_manager_priority_queue_get_attribute(self):
        queue = util.ManagerPriorityQueue()
        result = queue.get_attribute("queue")
        self.assertEqual([], result)

    def test_wrapper_manager(self):
        result = util.WrapperManager()
        self.assertIsInstance(result, util.WrapperManager)

    @patch("cryton_worker.lib.util.util.WrapperManager", Mock())
    def test_get_manager(self):
        result = util.get_manager()
        self.assertIsInstance(result, Mock)


class TestMetasploit(TestCase):
    @patch("cryton_worker.lib.util.util.MsfRpcClient")
    def setUp(self, mock_msf_client) -> None:
        self.mock_client = mock_msf_client
        self.msf = util.Metasploit()

    @patch("cryton_worker.lib.util.util.MsfRpcClient")
    def test_get_client_error(self, mock_client):
        mock_client.side_effect = Exception
        result = util.Metasploit()
        self.assertIsNotNone(result.error)

    @patch("cryton_worker.lib.util.util.MsfRpcClient")
    def test_get_client(self, mock_client):
        mock_client.return_value = Mock()
        result = util.Metasploit()
        self.assertIsNone(result.error)

    def test_is_connected(self):
        self.msf.error = None
        self.assertTrue(self.msf.is_connected())

    def test_is_not_connected(self):
        self.msf.error = Exception
        self.assertFalse(self.msf.is_connected())

    def test_get_sessions(self):
        self.mock_client.return_value.sessions.list = {"7": {"a": "ab", "b": "ab"}}
        ret = self.msf.get_sessions(**{"a": "b", "b": "ab"})
        self.assertEqual(["7"], ret)

    def test_get_sessions_fail(self):
        self.mock_client.return_value.sessions.list = {"7": {"a": "ab", "b": "ab"}}
        ret = self.msf.get_sessions(**{"a": "c", "b": "ab"})
        self.assertEqual([], ret)

    def test_execute_in_session(self):
        mock_session = Mock()
        mock_session.return_value.read.return_value = "test"
        self.mock_client.return_value.sessions.session = mock_session
        result = self.msf.execute_in_session("command", "session_id", None, True)
        self.assertEqual(result, "test")

    def test_execute_in_session_check_end(self):
        mock_session = Mock()
        mock_session.return_value.run_with_output.return_value = "test"
        self.mock_client.return_value.sessions.session = mock_session
        result = self.msf.execute_in_session("command", "session_id", "check_end", True)
        self.assertEqual(result, "test")

    def test_execute_exploit(self):
        mock_exploit, mock_payload = Mock(), Mock()
        self.mock_client.return_value.modules.use.side_effect = [mock_exploit, mock_payload]
        self.msf.execute_exploit("exploit", "payload")
        mock_exploit.execute.assert_called_once()


class TestModuleUtil(TestCase):
    def test_get_file_binary(self):
        tmp_file = "/tmp/test568425j4L.txt"
        with open(tmp_file, "w") as f:
            f.write("test")
        ret = module_util.get_file_binary(tmp_file)
        self.assertEqual(ret, b"test")
        os.remove(tmp_file)

    def test_file_validate_ok(self):
        file_test = module_util.File()
        test_variable = "test"
        with patch("os.path.isfile", return_value=True):
            ret = file_test.validate("test")
            self.assertEqual(test_variable, ret)

    def test_file_validate_fail(self):
        file_test = module_util.File()
        with patch("os.path.isfile", return_value=False):
            with self.assertRaises(Exception):
                file_test.validate("test")

    def test_file_validate_repr(self):
        file_test = module_util.File()
        self.assertEqual(file_test.__repr__(), "File()")

    def test_file_validate_err(self):
        file_test = module_util.File({"test": "test"})
        with self.assertRaises(Exception):
            file_test.validate("test")

    def test_file_validate_init(self):
        with self.assertRaises(TypeError):
            module_util.File(test="")

    def test_dir_validate_ok(self):
        dir_test = module_util.Dir()
        test_variable = "test"
        with patch("os.path.isdir", return_value=True):
            ret = dir_test.validate("test")
            self.assertEqual(test_variable, ret)

    def test_dir_validate_fail(self):
        dir_test = module_util.Dir()
        with patch("os.path.isdir", return_value=False):
            with self.assertRaises(Exception):
                dir_test.validate("test")

    def test_dir_validate_repr(self):
        dir_test = module_util.Dir()
        self.assertEqual(dir_test.__repr__(), "Dir()")

    def test_dir_validate_err(self):
        dir_test = module_util.Dir({"test": "test"})
        with self.assertRaises(Exception):
            dir_test.validate("test")

    def test_dir_validate_init(self):
        with self.assertRaises(TypeError):
            module_util.Dir(test="")

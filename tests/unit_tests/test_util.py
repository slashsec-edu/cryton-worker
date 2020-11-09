import os
from unittest import TestCase
from mock import patch, Mock

from cryton_worker.lib import util


class TestUtil(TestCase):

    @patch('cryton_worker.lib.util.run_executable')
    def test_execute_module(self, mock_run_executable):
        mock_run_executable.return_value = {'return_code': 0, 'file': {'file_contents': 'test'}}

        ret = util.execute_module('test', {'test': 'test'})
        self.assertEqual({'return_code': 0, 'file': {'file_contents': 'dGVzdA==', 'file_contents_encoding': 'base64'}},
                         ret)

    @patch('cryton_worker.lib.util.import_module')
    def test_run_executable(self, mock_import):
        mock = Mock()
        mock_import.return_value = mock
        mock.execute.return_value = {'return_code': 0}

        ret = util.run_executable('test', {'test': 'test'})
        self.assertEqual({'return_code': 0}, ret)

    @patch('cryton_worker.lib.util.import_module')
    def test_run_executable_import_err(self, mock_import):
        def raise_err():
            raise ModuleNotFoundError
        mock_import.side_effect = raise_err

        ret = util.run_executable('test', {'test': 'test'})
        self.assertEqual(-2, ret.get('return_code'))

    @patch('cryton_worker.lib.util.import_module')
    def test_run_executable_attrib_err(self, mock_import):
        def raise_err():
            raise AttributeError

        mock = Mock()
        mock.execute.side_effect = raise_err
        mock_import.return_value = mock

        ret = util.run_executable('test', {'test': 'test'})
        self.assertEqual(-1, ret.get('return_code'))

    @patch('cryton_worker.lib.util.import_module')
    def test_validate_module(self, mock_import):
        mock = Mock()
        mock_import.return_value = mock
        mock.validate.return_value = 0

        ret = util.validate_module('test', {'test': 'test'})
        self.assertEqual(0, ret.get('return_code'))

    @patch('cryton_worker.lib.util.import_module')
    def test_validate_module_import_err(self, mock_import):
        def raise_err():
            raise ModuleNotFoundError
        mock_import.side_effect = raise_err

        ret = util.validate_module('test', {'test': 'test'})
        self.assertEqual(-2, ret.get('return_code'))

    @patch('cryton_worker.lib.util.import_module')
    def test_validate_module_attrib_err(self, mock_import):
        def raise_err():
            raise AttributeError

        mock = Mock()
        mock.validate.side_effect = raise_err
        mock_import.return_value = mock

        ret = util.validate_module('test', {'test': 'test'})
        self.assertEqual(-1, ret.get('return_code'))

    @patch('importlib.import_module')
    def test_import_module(self, mock_import):
        util.import_module('test')
        mock_import.assert_called_once_with('test/mod')

    @patch('importlib.import_module')
    def test_import_module_missing_module(self, mock_import):
        def raise_err(*_):
            ex = ModuleNotFoundError(name='test')
            raise ex
        mock_import.side_effect = raise_err

        with self.assertRaises(ModuleNotFoundError):
            util.import_module('test')

    @patch('cryton_worker.lib.util.MsfRpcClient')
    def test_list_sessions(self, mock_msf):
        mock_custom = Mock()
        mock_custom.sessions.list = {1: {'target_host': 'test'}}
        mock_msf.return_value = mock_custom

        ret = util.list_sessions('test')
        self.assertEqual([1], ret)

    @patch('cryton_worker.etc.config.MODULES_DIR', '/tmp/mods4a4a5a7')
    def test_list_modules(self):
        ret = util.list_modules()
        self.assertEqual([], ret)

    def test_kill_execution(self):
        ret = util.kill_execution()
        self.assertEqual(ret, -1)

    def test_get_file_content(self):
        tmp_file = "/tmp/test568425j4L.txt"
        with open(tmp_file, "w") as f:
            f.write("test")
        ret = util.get_file_content(tmp_file)
        self.assertEqual(ret, b"test")
        os.remove(tmp_file)

    def test_file_validate(self):
        file_test = util.File()
        test_variable = "test"
        with patch('os.path.isfile', return_value=True):
            ret = file_test.validate('test')
            self.assertEqual(test_variable, ret)

        with patch('os.path.isfile', return_value=False):
            with self.assertRaises(Exception):
                file_test.validate('test')

    def test_dir_validate(self):
        dir_test = util.Dir()
        test_variable = "test"
        with patch('os.path.isdir', return_value=True):
            ret = dir_test.validate('test')
            self.assertEqual(test_variable, ret)

        with patch('os.path.isdir', return_value=False):
            with self.assertRaises(Exception):
                dir_test.validate('test')


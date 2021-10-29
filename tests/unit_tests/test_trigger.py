from unittest import TestCase
from mock import patch, Mock

from cryton_worker.lib.triggers import HTTPTrigger, Trigger, TriggerEnum, exceptions, MSFTrigger
from cryton_worker.lib.util import constants as co


class TestTriggerEnum(TestCase):
    def test_get_correct_item(self):
        result = TriggerEnum["HTTP"]
        self.assertEqual(result, HTTPTrigger)

    def test_get_wrong_item(self):
        with self.assertRaises(exceptions.TriggerTypeDoesNotExist):
            _ = TriggerEnum["WRONG"]


class TestTrigger(TestCase):
    def setUp(self):
        self.mock_main_queue = Mock()
        self.trigger_obj = Trigger("host", 1, self.mock_main_queue)

    def test_compare_identifiers_match(self):
        result = self.trigger_obj.compare_identifiers(Trigger, "host", 1)
        self.assertTrue(result)

    def test_compare_identifiers_no_match(self):
        result = self.trigger_obj.compare_identifiers(Trigger, "host", 10)
        self.assertFalse(result)

    def test_start(self):
        self.trigger_obj.start()

    def test_stop(self):
        self.trigger_obj.stop()

    def test_add_activator(self):
        self.trigger_obj.add_activator({})

    def test_remove_activator(self):
        self.trigger_obj.remove_activator({})

    def test_find_activator(self):
        self.assertIsNone(self.trigger_obj.find_activator(""))  # No activator is found

        test_activator = {co.TRIGGER_ID: "test_id"}
        self.trigger_obj._activators.append(test_activator)
        result = self.trigger_obj.find_activator("test_id")
        self.assertEqual(result, test_activator)

    def test_get_activators(self):
        test_activator = {co.TRIGGER_ID: "test_id"}
        self.trigger_obj._activators.append(test_activator)
        result = self.trigger_obj.get_activators()
        self.assertEqual(result, [test_activator])

    def test_any_activator_exists_true(self):
        self.trigger_obj._activators.append({})
        result = self.trigger_obj.any_activator_exists()
        self.assertTrue(result)

    def test_any_activator_exists_false(self):
        result = self.trigger_obj.any_activator_exists()
        self.assertFalse(result)

    def test__notify(self):
        q_name = "queue_name"
        msg_body = {}
        self.trigger_obj._notify(q_name, msg_body)
        self.mock_main_queue.put.assert_called_once()


class TestHTTPTrigger(TestCase):
    @patch("bottle.Bottle", Mock())
    def setUp(self):
        self.mock_main_queue = Mock()
        self.trigger_obj = HTTPTrigger("test", 1, self.mock_main_queue)
        self.details = {"type": "HTTP", "host": "test", "port": 8082, "event_q": "test", "stage_ex_id": 1, "routes": [
            {"path": "test", "method": "GET", "parameters": [{"name": "a", "value": "1"}]}]}

    @patch("cryton_worker.lib.triggers.trigger_http.HTTPTrigger._restart")
    def test_add_activator(self, mock_restart):
        self.trigger_obj.add_activator(self.details)
        mock_restart.assert_called()

    @patch("cryton_worker.lib.triggers.trigger_http.HTTPTrigger._restart")
    def test_remove_activator(self, mock_restart):
        self.trigger_obj._activators.append(self.details)
        self.trigger_obj.remove_activator(self.details)
        mock_restart.assert_called()

    @patch("cryton_worker.lib.triggers.trigger_http.HTTPTrigger.stop")
    def test__restart_only_stop(self, mock_stop):
        self.trigger_obj._stopped = False
        self.trigger_obj._restart()
        mock_stop.assert_called()

    @patch("cryton_worker.lib.triggers.trigger_http.HTTPTrigger.start")
    @patch("cryton_worker.lib.triggers.trigger_http.HTTPTrigger.stop")
    def test__restart(self, mock_stop, mock_start):
        self.trigger_obj._stopped = False
        self.trigger_obj._activators.append(self.details)
        self.trigger_obj._restart()
        mock_stop.assert_called()
        mock_start.assert_called()

    def test_get_activators_num(self):
        self.trigger_obj._activators.append(self.details)
        ret = self.trigger_obj.any_activator_exists()
        self.assertEqual(ret, 1)

    @patch("cryton_worker.lib.triggers.trigger_http.HTTPTrigger._check_parameters")
    @patch("cryton_worker.lib.triggers.trigger_http.HTTPTrigger._notify")
    @patch("bottle.request")
    def test__handle_request(self, mock_req, mock_send, mock_params):
        mock_req.method = "GET"
        mock_req.path = "test"
        mock_params.return_value = True
        self.trigger_obj._activators.append(self.details)
        self.trigger_obj._handle_request()
        mock_send.assert_called()

    @patch("bottle.request")
    def test__check_parameters_get_ok(self, mock_req):
        mock_req.method = "GET"
        mock_req.query = {"tire": 15, "hammer": 25}
        parameters = [{"name": "tire", "value": 15}, {"name": "hammer", "value": 25}]
        ret = self.trigger_obj._check_parameters(parameters)
        self.assertTrue(ret)

    @patch("bottle.request")
    def test__check_parameters_get_fail(self, mock_req):
        mock_req.method = "GET"
        mock_req.query = {"tire": 99}
        parameters = [{"name": "tire", "value": 15}]
        ret = self.trigger_obj._check_parameters(parameters)
        self.assertFalse(ret)

    @patch("bottle.request")
    def test__check_parameters_post_ok(self, mock_req):
        mock_req.method = "POST"
        mock_req.forms = {"tire": 15, "hammer": 25}
        parameters = [{"name": "tire", "value": 15}, {"name": "hammer", "value": 25}]
        ret = self.trigger_obj._check_parameters(parameters)
        self.assertTrue(ret)

    @patch("bottle.request")
    def test__check_parameters_post_fail(self, mock_req):
        mock_req.method = "POST"
        mock_req.forms = {"tire": 99}
        parameters = [{"name": "tire", "value": 15}]
        ret = self.trigger_obj._check_parameters(parameters)
        self.assertFalse(ret)

    @patch("bottle.request")
    def test__check_parameters_fail(self, mock_req):
        mock_req.method = "DELETE"
        mock_req.forms = {"tire": 99}
        parameters = [{"name": "tire", "value": 15}]
        ret = self.trigger_obj._check_parameters(parameters)
        self.assertFalse(ret)

    @patch("multiprocessing.Process.start")
    def test_start(self, mock_start):
        self.trigger_obj._stopped = True
        self.trigger_obj.start()
        mock_start.assert_called()
        self.assertIsNotNone(self.trigger_obj._process)

    def test_stop(self):
        self.trigger_obj._stopped = False
        mock_process = Mock()
        self.trigger_obj._process = mock_process

        self.trigger_obj.stop()
        mock_process.terminate.assert_called()
        self.assertIsNone(self.trigger_obj._process)


class TestMSFTrigger(TestCase):
    @patch("cryton_worker.lib.util.util.Metasploit")
    def setUp(self, mock_msf):
        self.mock_msf = mock_msf
        self.mock_msf.is_connected.return_value = True
        self.mock_main_queue = Mock()
        self.trigger_obj = MSFTrigger("test", 1, self.mock_main_queue)
        self.details = {"type": "MSF", 'host': "", 'port': 1, "reply_to": "", "exploit": "", "exploit_arguments": {},
                        "payload": "", "payload_arguments": {}}

    @patch("cryton_worker.lib.triggers.trigger_msf.MSFTrigger.start")
    @patch("cryton_worker.lib.triggers.trigger_base.Trigger._generate_id")
    def test_add_activator(self, mock_gen, mock_start):
        mock_gen.return_value = "1"
        result = self.trigger_obj.add_activator(self.details)
        self.assertEqual(result, "1")
        mock_start.assert_called_once()

    @patch("cryton_worker.lib.triggers.trigger_msf.MSFTrigger.any_activator_exists")
    def test_add_activator_error(self, mock_exists):
        mock_exists.return_value = True
        with self.assertRaises(exceptions.TooManyActivators):
            self.trigger_obj.add_activator(self.details)

    @patch("cryton_worker.lib.triggers.trigger_msf.MSFTrigger.stop")
    def test_remove_activator(self, mock_stop):
        self.trigger_obj._activators.append(self.details)
        self.trigger_obj.remove_activator(self.details)
        mock_stop.assert_called_once()

    @patch("time.sleep", Mock())
    @patch("cryton_worker.lib.triggers.trigger_msf.MSFTrigger._notify")
    def test__check_for_session(self, mock_notify):
        self.mock_msf.return_value.get_sessions.side_effect = [[], ["1"]]
        self.trigger_obj._activators.append(self.details)
        self.trigger_obj._stopped = False
        self.trigger_obj._check_for_session()
        mock_notify.assert_called_once()

    @patch("copy.deepcopy", Mock())
    @patch("threading.Thread.start")
    def test_start(self, mock_thread):
        self.trigger_obj._activators.append(self.details)
        self.trigger_obj.start()
        self.assertFalse(self.trigger_obj._stopped)
        mock_thread.assert_called_once()

    def test_stop(self):
        self.trigger_obj._stopped = False
        self.trigger_obj.stop()
        self.assertTrue(self.trigger_obj._stopped)

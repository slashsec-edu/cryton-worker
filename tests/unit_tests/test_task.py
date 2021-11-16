from unittest import TestCase
from mock import patch, Mock
from schema import SchemaError

from cryton_worker.lib import task
from cryton_worker.lib.util import constants as co


class TestTask(TestCase):
    @patch("cryton_worker.lib.task.Process", Mock())
    def setUp(self):
        self.mock_main_queue = Mock()
        self.message = Mock()
        self.task_obj = task.Task(self.message, self.mock_main_queue)

    @patch("json.dumps", Mock())
    @patch("json.loads", Mock())
    @patch("cryton_worker.lib.task.Task._execute", Mock())
    @patch("cryton_worker.lib.task.Task._validate", Mock())
    @patch("cryton_worker.lib.task.Task.reply", Mock())
    def test___call__(self):
        self.task_obj()
        self.mock_main_queue.put.assert_called_once()

    @patch("json.dumps")
    @patch("json.loads", Mock())
    @patch("cryton_worker.lib.task.Task._execute", Mock())
    @patch("cryton_worker.lib.task.Task._validate")
    @patch("cryton_worker.lib.task.Task.reply", Mock())
    def test___call___err(self, mock_validate, mock_dumps):
        mock_validate.side_effect = SchemaError("")
        self.task_obj()
        mock_dumps.assert_called_once_with({"return_code": -2, "std_err": ""})
        self.mock_main_queue.put.assert_called_once()

    def test__validate(self):
        self.task_obj._validate({})

    def test__execute(self):
        self.task_obj._execute({})

    @patch("json.dumps", Mock())
    @patch("cryton_worker.lib.task.Task.reply")
    def test_kill(self, mock_reply):
        self.task_obj.kill()
        mock_reply.assert_called()

    def test_join(self):
        self.assertIsNone(self.task_obj.join())

    def test_start(self):
        self.assertIsNone(self.task_obj.start())

    @patch("amqpstorm.Message.create")
    def test__reply(self, mock_create):
        self.task_obj.reply("")
        mock_create.assert_called_once()


class TestAttackTask(TestCase):
    @patch("cryton_worker.lib.task.Process", Mock())
    def setUp(self):
        self.mock_main_queue = Mock()
        self.message = Mock()
        self.task_obj = task.AttackTask(self.message, self.mock_main_queue)

    def test__validate(self):
        self.task_obj._validate({co.ARGUMENTS: {co.ATTACK_MODULE: "", co.ATTACK_MODULE_ARGUMENTS: {}},
                                 co.STEP_TYPE: co.STEP_TYPE_EXECUTE_ON_WORKER, co.ACK_QUEUE: "queue"})

    def test__validate_error(self):
        with self.assertRaises(SchemaError):
            self.task_obj._validate({})

    @patch("cryton_worker.lib.util.util.run_attack_module_on_worker")
    def test__execute_on_worker(self, mock_execute_mod):
        mock_execute_mod.return_value = 0
        result = self.task_obj._execute({co.ACK_QUEUE: "test_que",
                                         co.STEP_TYPE: co.STEP_TYPE_EXECUTE_ON_WORKER,
                                         co.ARGUMENTS: {
                                             co.ATTACK_MODULE: "test_module",
                                             co.ATTACK_MODULE_ARGUMENTS: {}
                                         }})
        self.assertEqual(result, 0)

    @patch("cryton_worker.lib.empire.EmpireClient.execute_on_agent")
    def test__execute_on_agent(self, mock_execute_on_agent):
        mock_execute_on_agent.return_value = 0
        result = self.task_obj._execute({co.ACK_QUEUE: "test_que",
                                        co.STEP_TYPE: co.STEP_TYPE_EXECUTE_ON_AGENT,
                                        co.ARGUMENTS: {
                                             co.USE_AGENT: "test_agent",
                                             co.EMPIRE_MODULE: "test_module"
                                        }})
        self.assertEqual(result, 0)


class TestControlTask(TestCase):
    @patch("cryton_worker.lib.task.Process", Mock())
    def setUp(self):
        self.mock_main_queue = Mock()
        self.message = Mock()
        self.task_obj = task.ControlTask(self.message, self.mock_main_queue)

    def test__validate(self):
        self.task_obj._validate({co.EVENT_T: "name", co.EVENT_V: {}})

    def test__validate_error(self):
        with self.assertRaises(SchemaError):
            self.task_obj._validate({})

    @patch("cryton_worker.lib.event.Event.list_modules")
    def test__execute(self, mock_list):
        mock_list.return_value = 0
        result = self.task_obj._execute({co.EVENT_T: co.EVENT_LIST_MODULES, co.EVENT_V: ""})
        self.assertEqual(result, {co.EVENT_T: co.EVENT_LIST_MODULES, co.EVENT_V: 0})

    def test__execute_unknown_event(self):
        event_type = "UNKNOWN"
        result = self.task_obj._execute({co.EVENT_T: event_type, co.EVENT_V: ""})
        self.assertEqual(result, {co.EVENT_T: event_type, co.EVENT_V: {
            co.RETURN_CODE: co.CODE_ERROR, co.STD_ERR: f"Unknown event type: {event_type}."}})

    @patch("cryton_worker.lib.event.Event.list_modules")
    def test__execute_error(self, mock_list):
        mock_list.side_effect = Exception
        result = self.task_obj._execute({co.EVENT_T: co.EVENT_LIST_MODULES, co.EVENT_V: ""})
        self.assertEqual(result.get(co.EVENT_T), co.EVENT_LIST_MODULES)
        self.assertIsNotNone(result.get(co.EVENT_V).get(co.STD_ERR))

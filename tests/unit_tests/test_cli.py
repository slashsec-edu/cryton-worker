from unittest import TestCase
from mock import patch, Mock
from click.testing import CliRunner

from cryton_worker.cli import cli


class CliTest(TestCase):
    def setUp(self):
        self.runner = CliRunner()

    def test_cli(self):
        result = self.runner.invoke(cli)
        self.assertEqual(0, result.exit_code)

    @patch('cryton_worker.lib.worker.start', Mock())
    def test_start(self):
        result = self.runner.invoke(cli, ['start'])
        self.assertEqual(0, result.exit_code)

import unittest

from alerta.commands import create_app
from alerta.commands import key as key_cmd
from alerta.commands import keys as keys_cmd
from alerta.commands import user as user_cmd
from alerta.commands import users as users_cmd


class CommandsTestCase(unittest.TestCase):

    def setUp(self):
        test_config = {
            'TESTING': True,
            'ADMIN_USERS': ['admin@alerta.io', 'foo@bar.com', 'satterly', 'me@work.com'],
            'AUTH_PROVIDER': 'basic'
        }
        self.app = create_app(test_config)
        self.runner = self.app.test_cli_runner(echo_stdin=True)

    def test_key_cmd(self):

        result = self.runner.invoke(key_cmd, ['--all'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn('me@work.com', result.output.strip())

    def test_keys_cmd(self):

        result = self.runner.invoke(keys_cmd)
        self.assertEqual(result.exit_code, 0)
        self.assertIn('me@work.com', result.output.strip())

    def test_user_cmd(self):

        result = self.runner.invoke(user_cmd, ['--password', 'pa55w0rd', '--all'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn('me@work.com', result.output.strip())

    def test_users_cmd(self):

        result = self.runner.invoke(users_cmd)
        self.assertEqual(result.exit_code, 0)
        self.assertIn('me@work.com', result.output.strip())

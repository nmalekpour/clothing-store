"""Exercise fixed Console initialization SQL and repeat-safe order migration without a server."""
import importlib.util
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('setup_service', ROOT / 'lambda_function.py')
service = importlib.util.module_from_spec(spec)
# No driver installation is needed for local tests.
with patch.dict(sys.modules, {'pymysql': MagicMock()}):
    spec.loader.exec_module(service)


class SetupTests(unittest.TestCase):
    def run_setup(self, target, existing=0):
        connection = MagicMock()
        cursor = connection.__enter__.return_value.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = (existing,)
        env = {'SETUP_TARGET': target, 'DB_HOST': 'test', 'DB_USER': 'admin', 'DB_PASSWORD': 'test',
               'APP_DB_USER': 'service_app', 'APP_DB_PASSWORD': 'synthetic-password'}
        with patch.dict(os.environ, env, clear=True), patch.object(service, 'ROOT', ROOT.parent / 'db'), \
             patch.object(service.pymysql, 'connect', return_value=connection):
            result = service.lambda_handler({'sql': 'DROP DATABASE clothingstore'}, None)
        return result, [call.args for call in cursor.execute.call_args_list]

    def test_payment_and_shipping_only_run_fixed_sql_and_scoped_grants(self):
        for target in ('payment', 'shipping'):
            result, calls = self.run_setup(target)
            sql = '\n'.join(call[0] for call in calls)
            self.assertEqual(result['initialized'], target)
            self.assertIn('CREATE TABLE IF NOT EXISTS', sql)
            self.assertIn(f'GRANT SELECT, INSERT ON {target}db.', sql)
            self.assertNotIn('DROP', sql)
            self.assertNotIn('clothingstore', sql)

    def test_migration_adds_column_only_when_missing(self):
        _, calls = self.run_setup('order')
        self.assertTrue(any('ALTER TABLE' in call[0] for call in calls))
        _, calls = self.run_setup('order', existing=1)
        self.assertFalse(any('ALTER TABLE' in call[0] for call in calls))


if __name__ == '__main__':
    unittest.main()

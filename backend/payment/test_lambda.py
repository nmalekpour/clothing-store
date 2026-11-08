"""Run locally without AWS or MySQL: python3 -B backend/payment/test_lambda.py"""
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lambda_function as service
from test_db import Connection

PAYMENT = {'amount': 12.34, 'orderReference': 'CS-test', 'payment': {
    'cardholderName': 'Lab Test', 'cardNumber': '4111111111111111',
    'expirationDate': '12/30', 'cvv': '123'}}


class PaymentTests(unittest.TestCase):
    def setUp(self):
        self.db = Connection(Path(__file__).resolve().parents[1] / 'db/payment.sql')
        self.addCleanup(self.db.close)

    def call(self, body):
        with patch.object(service, 'connect', return_value=self.db):
            response = service.lambda_handler({'httpMethod': 'POST', 'body': json.dumps(body)}, None)
        return response['statusCode'], json.loads(response['body'])

    def test_token_returned_only_after_save_and_cvv_not_stored(self):
        status, body = self.call(PAYMENT)
        self.assertEqual(status, 200)
        self.assertTrue(body['paymentToken'].startswith('PAY-'))
        self.assertEqual(self.db.query('SELECT PAYMENT_TOKEN, AMOUNT, ORDER_REFERENCE FROM PAYMENT'),
                         [(body['paymentToken'], 12.34, 'CS-test')])
        columns = [row[1] for row in self.db.query('PRAGMA table_info(PAYMENT)')]
        self.assertNotIn('CVV', columns)
        self.assertNotIn(PAYMENT['payment']['cardNumber'], json.dumps(body))

    def test_invalid_payment_does_not_persist(self):
        for body in [None, [], {}, {**PAYMENT, 'amount': True}, {**PAYMENT, 'amount': -1},
                     {**PAYMENT, 'amount': float('nan')}, {**PAYMENT, 'amount': 1.001},
                     {**PAYMENT, 'payment': {**PAYMENT['payment'], 'cvv': ''}},
                     {**PAYMENT, 'payment': {**PAYMENT['payment'], 'expirationDate': '99/30'}},
                     {**PAYMENT, 'payment': {**PAYMENT['payment'], 'cardNumber': 'bad'}}]:
            self.assertEqual(self.call(body)[0], 400)
        self.assertEqual(self.db.query('SELECT COUNT(*) FROM PAYMENT'), [(0,)])

    def test_database_failure_never_returns_token_or_logs_card(self):
        with patch.object(service, 'connect', side_effect=OSError('secret-card-data')), patch('builtins.print') as logged:
            result = service.lambda_handler({'body': json.dumps(PAYMENT)}, None)
        self.assertEqual(result['statusCode'], 502)
        self.assertNotIn('paymentToken', result['body'])
        self.assertNotIn('secret-card-data', str(logged.call_args))

    def test_http_methods_and_bad_json(self):
        self.assertEqual(service.lambda_handler({'httpMethod': 'OPTIONS'}, None)['statusCode'], 204)
        self.assertEqual(service.lambda_handler({'httpMethod': 'GET'}, None)['statusCode'], 405)
        self.assertEqual(service.lambda_handler({'body': '{'}, None)['statusCode'], 400)


if __name__ == '__main__':
    unittest.main()

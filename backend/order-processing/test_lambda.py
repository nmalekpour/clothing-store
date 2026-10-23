"""Run: python3 -B backend/order-processing/test_lambda.py"""
import json
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(__file__))
from lambda_function import lambda_handler

PRODUCT = {'id': 0, 'name': 'Test shirt', 'price': 0.10, 'description': 'Test', 'image': '/test.jpg', 'availableQty': 12}
INVENTORY = [PRODUCT, {**PRODUCT, 'id': 1, 'price': 19.99, 'availableQty': 2}]
DETAILS = {'payment': {'cardNumber': '4111111111111111'}, 'shipping': {'fullName': 'Lab Test'}}


class OrderTests(unittest.TestCase):
    def call(self, items, **extra):
        order = {**DETAILS, 'items': items, **extra}
        with patch('lambda_function.inventory_items', return_value=INVENTORY):
            response = lambda_handler({'httpMethod': 'POST', 'body': json.dumps(order)}, None)
        self.assertEqual(response['headers']['Access-Control-Allow-Origin'], '*')
        return response['statusCode'], json.loads(response['body'])

    def test_success_uses_inventory_prices_and_decimal_totals(self):
        status, body = self.call([{'id': 0, 'quantity': 3}, {'id': 1, 'quantity': 2}])
        self.assertEqual(status, 200)
        self.assertTrue(body['confirmationNumber'].startswith('CS-'))
        self.assertEqual(body['total'], 40.28)
        self.assertEqual(body['items'][0]['subtotal'], 0.3)
        self.assertEqual(body['itemCount'], 5)

    def test_duplicate_lines_exceeding_combined_stock_fail(self):
        status, body = self.call([{'id': 0, 'quantity': 7}, {'id': 0, 'quantity': 7}])
        self.assertEqual(status, 409)
        self.assertEqual(body['unavailable'], [{'id': 0, 'requestedQty': 14, 'availableQty': 12}])
        self.assertNotIn('confirmationNumber', body)

    def test_duplicate_lines_within_stock_are_merged(self):
        status, body = self.call([{'id': 0, 'quantity': 2}, {'id': 0, 'quantity': 3}])
        self.assertEqual(status, 200)
        self.assertEqual(len(body['items']), 1)
        self.assertEqual(body['items'][0]['quantity'], 5)
        self.assertEqual(body['total'], 0.5)

    def test_exact_stock_succeeds(self):
        self.assertEqual(self.call([{'id': 0, 'quantity': 12}])[0], 200)

    def test_unknown_item_fails(self):
        status, body = self.call([{'id': 99, 'quantity': 1}])
        self.assertEqual(status, 409)
        self.assertEqual(body['unavailable'][0]['availableQty'], 0)

    def test_client_price_and_subtotal_are_ignored(self):
        status, body = self.call([{'id': 1, 'quantity': 2, 'price': 0.01, 'subtotal': 0.02}], total=0.02)
        self.assertEqual(status, 200)
        self.assertEqual(body['total'], 39.98)

    def test_preview_needs_no_personal_data_and_never_confirms(self):
        with patch('lambda_function.uuid.uuid4') as confirmation:
            status, body = self.call([{'id': 0, 'quantity': 1}], preview=True, payment={}, shipping={})
        self.assertEqual(status, 200)
        self.assertEqual(body['total'], 0.1)
        self.assertNotIn('confirmationNumber', body)
        confirmation.assert_not_called()

    def test_preview_reports_merged_shortages(self):
        status, body = self.call([{'id': 0, 'quantity': 7}, {'id': 0, 'quantity': 7}], preview=True)
        self.assertEqual(status, 200)
        self.assertEqual(body['unavailable'][0]['requestedQty'], 14)

    def test_empty_preview(self):
        status, body = self.call([], preview=True)
        self.assertEqual((status, body['total'], body['itemCount']), (200, 0, 0))

    def test_price_change_requires_customer_review(self):
        status, body = self.call([{'id': 1, 'quantity': 1}], expectedTotal=15)
        self.assertEqual(status, 409)
        self.assertTrue(body['priceChanged'])
        self.assertNotIn('confirmationNumber', body)
        self.assertEqual(self.call([{'id': 1, 'quantity': 1}], expectedTotal=19.99)[0], 200)

    def test_invalid_requests(self):
        for items in [[], [{'id': '0', 'quantity': 1}], [{'id': True, 'quantity': 1}], [{'id': 0, 'quantity': True}], [{'id': 0, 'quantity': 0}], [{'id': 0, 'quantity': 1.5}]]:
            with self.subTest(items=items):
                self.assertEqual(self.call(items)[0], 400)
        self.assertEqual(self.call([{'id': 0, 'quantity': 1}], payment={})[0], 400)
        self.assertEqual(self.call([{'id': 0, 'quantity': 1}], shipping={})[0], 400)
        self.assertEqual(self.call([{'id': 0, 'quantity': 1}], preview='true')[0], 400)
        self.assertEqual(self.call([{'id': 0, 'quantity': 1}], expectedTotal=float('nan'))[0], 400)

    def test_inventory_failure_does_not_confirm(self):
        with patch('lambda_function.inventory_items', side_effect=OSError('offline')):
            result = lambda_handler({'body': json.dumps({**DETAILS, 'items': [{'id': 0, 'quantity': 1}]})}, None)
        self.assertEqual(result['statusCode'], 502)
        self.assertNotIn('confirmationNumber', json.loads(result['body']))

    def test_invalid_inventory_price_fails(self):
        for price in [float('nan'), float('inf'), -1, True]:
            with patch('lambda_function.inventory_items', return_value=[{**PRODUCT, 'price': price}]):
                result = lambda_handler({'body': json.dumps({**DETAILS, 'items': [{'id': 0, 'quantity': 1}]})}, None)
            self.assertEqual(result['statusCode'], 502)

    def test_options_bad_json_and_method(self):
        self.assertEqual(lambda_handler({'httpMethod': 'OPTIONS'}, None)['statusCode'], 204)
        self.assertEqual(lambda_handler({'body': '{not json'}, None)['statusCode'], 400)
        self.assertEqual(lambda_handler({'httpMethod': 'GET'}, None)['statusCode'], 405)


if __name__ == '__main__':
    unittest.main()

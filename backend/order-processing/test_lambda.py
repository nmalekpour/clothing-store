"""Run: python3 -B backend/order-processing/test_lambda.py"""
import json
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import lambda_function
from lambda_function import lambda_handler
from test_db import Connection

PRODUCT = {'id': 0, 'name': 'Test shirt', 'price': 0.10, 'description': 'Test', 'image': '/test.jpg', 'availableQty': 12}
INVENTORY = [PRODUCT, {**PRODUCT, 'id': 1, 'price': 19.99, 'availableQty': 2}]
DETAILS = {'payment': {'cardholderName': 'Lab Test', 'cardNumber': '4111111111111111', 'expirationDate': '12/30',
                       'cvv': '123', 'billingZip': '43210'},
           'shipping': {'fullName': 'Lab Test', 'address': '1 Main St', 'city': 'Columbus', 'state': 'OH', 'zip': '43210'}}


def database(inventory=INVENTORY):
    db = Connection()
    db.query('DELETE FROM ITEM')
    for product in inventory:
        db.query('INSERT INTO ITEM (ITEM_NUMBER, NAME, DESCRIPTION, AVAILABLE_QUANTITY, UNIT_PRICE, IMAGE) '
                 'VALUES (?, ?, ?, ?, ?, ?)', (product['id'], product['name'], product['description'],
                                               product['availableQty'], product['price'], product['image']))
    return db


def post(db, body):
    with patch('lambda_function.connect', return_value=db):
        return lambda_handler({'httpMethod': 'POST', 'body': json.dumps(body)}, None)


class OrderTests(unittest.TestCase):
    def setUp(self):
        self.db = database()
        self.addCleanup(self.db.close)

    def call(self, items, **extra):
        response = post(self.db, {**DETAILS, 'items': items, **extra})
        self.assertEqual(response['headers']['Access-Control-Allow-Origin'], '*')
        return response['statusCode'], json.loads(response['body'])

    def order_count(self):
        return self.db.query('SELECT COUNT(*) FROM CUSTOMER_ORDER')[0][0]

    def test_confirmed_order_is_saved_and_stock_reduced(self):
        status, body = self.call([{'id': 0, 'quantity': 3}, {'id': 1, 'quantity': 2}])
        self.assertEqual(status, 200)
        order = self.db.query('SELECT ID, CONFIRMATION_NUMBER, CUSTOMER_NAME, STATUS, TOTAL, '
                              'SHIPPING_INFO_ID_FK, PAYMENT_INFO_ID_FK FROM CUSTOMER_ORDER')
        self.assertEqual(len(order), 1)
        order_id, confirmation, name, order_status, total, shipping_id, payment_id = order[0]
        self.assertEqual((confirmation, name, order_status, total), (body['confirmationNumber'], 'Lab Test', 'New', 40.28))
        self.assertEqual(self.db.query('SELECT NAME, ADDRESS1, CITY, POSTAL_CODE FROM SHIPPING_INFO WHERE ID = ?', (shipping_id,)),
                         [('Lab Test', '1 Main St', 'Columbus', '43210')])
        self.assertEqual(self.db.query('SELECT HOLDER_NAME, EXP_DATE FROM PAYMENT_INFO WHERE ID = ?', (payment_id,)),
                         [('Lab Test', '12/30')])
        self.assertEqual(self.db.query('SELECT ITEM_ID, ITEM_NAME, QUANTITY, UNIT_PRICE FROM CUSTOMER_ORDER_LINE_ITEM '
                                       'WHERE CUSTOMER_ORDER_ID_FK = ? ORDER BY ITEM_ID', (order_id,)),
                         [(0, 'Test shirt', 3, 0.1), (1, 'Test shirt', 2, 19.99)])
        self.assertEqual(self.db.query('SELECT AVAILABLE_QUANTITY FROM ITEM ORDER BY ITEM_NUMBER'), [(9,), (0,)])

    def test_stock_reduction_blocks_overselling(self):
        self.assertEqual(self.call([{'id': 1, 'quantity': 2}])[0], 200)
        status, body = self.call([{'id': 1, 'quantity': 1}])
        self.assertEqual(status, 409)
        self.assertEqual(body['unavailable'], [{'id': 1, 'requestedQty': 1, 'availableQty': 0}])

    def test_failed_save_rolls_back(self):
        with patch('lambda_function.save_order', side_effect=ValueError('boom')):
            self.assertEqual(self.call([{'id': 0, 'quantity': 1}])[0], 502)
        self.assertEqual(self.order_count(), 0)
        self.assertEqual(self.db.query('SELECT AVAILABLE_QUANTITY FROM ITEM WHERE ITEM_NUMBER = 0'), [(12,)])

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
        self.assertEqual(self.order_count(), 0)

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
        self.assertEqual(self.order_count(), 0)

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

    def test_missing_database_settings_do_not_confirm(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(lambda_function, '_connection', None):
            result = lambda_handler({'body': json.dumps({**DETAILS, 'items': [{'id': 0, 'quantity': 1}]})}, None)
        self.assertEqual(result['statusCode'], 502)
        self.assertNotIn('confirmationNumber', json.loads(result['body']))

    def test_invalid_inventory_price_fails(self):
        for price in [None, float('inf'), -1]:
            with self.subTest(price=price):
                db = database([{**PRODUCT, 'price': price}])
                result = post(db, {**DETAILS, 'items': [{'id': 0, 'quantity': 1}]})
                self.assertEqual(result['statusCode'], 502)
                self.assertEqual(db.query('SELECT COUNT(*) FROM CUSTOMER_ORDER'), [(0,)])
                db.close()

    def test_options_bad_json_and_method(self):
        self.assertEqual(lambda_handler({'httpMethod': 'OPTIONS'}, None)['statusCode'], 204)
        self.assertEqual(lambda_handler({'body': '{not json'}, None)['statusCode'], 400)
        self.assertEqual(lambda_handler({'httpMethod': 'GET'}, None)['statusCode'], 405)


if __name__ == '__main__':
    unittest.main()

"""Run: python3 -B backend/order-processing/test_lambda.py"""
import json
import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from contextlib import ExitStack

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import lambda_function
from lambda_function import lambda_handler
from test_db import Connection
fetch_inventory_original = lambda_function.fetch_inventory
process_payment_original = lambda_function.process_payment
publish_shipping_original = lambda_function.publish_shipping

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
        self.contexts = ExitStack()
        self.addCleanup(self.contexts.close)
        self.db = database()
        self.addCleanup(self.db.close)
        for name, value in [('fetch_inventory', INVENTORY), ('process_payment', 'PAY-test'), ('publish_shipping', None)]:
            mock = self.contexts.enter_context(patch.object(lambda_function, name, return_value=value))
            setattr(self, name, mock)
        self.contexts.enter_context(patch.dict(os.environ, {'EVENT_BUS_NAME': 'default', 'BUSINESS_ID': 'LAB-001'}))

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
                              'SHIPPING_INFO_ID_FK, PAYMENT_TOKEN FROM CUSTOMER_ORDER')
        self.assertEqual(len(order), 1)
        order_id, confirmation, name, order_status, total, shipping_id, payment_token = order[0]
        self.assertEqual((confirmation, name, order_status, total), (body['confirmationNumber'], 'Lab Test', 'New', 40.28))
        self.assertEqual(self.db.query('SELECT NAME, ADDRESS1, CITY, POSTAL_CODE FROM SHIPPING_INFO WHERE ID = ?', (shipping_id,)),
                         [('Lab Test', '1 Main St', 'Columbus', '43210')])
        self.assertEqual(payment_token, 'PAY-test')
        self.assertEqual(self.db.query('SELECT COUNT(*) FROM PAYMENT_INFO'), [(0,)])
        self.assertEqual(self.db.query('SELECT PAYMENT_INFO_ID_FK FROM CUSTOMER_ORDER'), [(None,)])
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

    def test_payment_failure_rolls_back_without_shipping(self):
        self.process_payment.side_effect = lambda_function.PaymentRejected('declined')
        self.assertEqual(self.call([{'id': 0, 'quantity': 1}])[0], 402)
        self.assertEqual(self.order_count(), 0)
        self.assertEqual(self.db.query('SELECT AVAILABLE_QUANTITY FROM ITEM WHERE ITEM_NUMBER = 0'), [(12,)])
        self.publish_shipping.assert_not_called()

    def test_payment_timeout_rolls_back(self):
        self.process_payment.side_effect = TimeoutError()
        self.assertEqual(self.call([{'id': 0, 'quantity': 1}])[0], 502)
        self.assertEqual(self.order_count(), 0)
        self.publish_shipping.assert_not_called()

    def test_shipping_failure_preserves_confirmation_and_stock(self):
        self.publish_shipping.side_effect = RuntimeError('unavailable')
        status, body = self.call([{'id': 0, 'quantity': 3}])
        self.assertEqual(status, 200)
        self.assertEqual(body['shippingStatus'], 'pending_manual_replay')
        self.assertEqual(self.order_count(), 1)
        self.assertEqual(self.db.query('SELECT AVAILABLE_QUANTITY FROM ITEM WHERE ITEM_NUMBER = 0'), [(9,)])

    def test_event_is_sent_only_after_commit_and_contains_no_payment(self):
        observed = []
        self.publish_shipping.side_effect = lambda shipment: observed.append(
            (self.order_count(), self.db.db.in_transaction, shipment))
        self.assertEqual(self.call([{'id': 0, 'quantity': 2}, {'id': 0, 'quantity': 3}, {'id': 1, 'quantity': 2}],
                                   shipping={**DETAILS['shipping'], 'payment': DETAILS['payment']})[0], 200)
        self.assertEqual(len(observed), 1)
        count, in_transaction, shipment = observed[0]
        self.assertEqual(count, 1)
        self.assertFalse(in_transaction)
        self.assertEqual(shipment['packetWeightsLb'], [5.0, 2.0])
        self.assertEqual(shipment['packetCount'], 2)
        self.assertEqual(shipment['businessId'], 'LAB-001')
        self.assertNotIn('payment', shipment)
        self.assertNotIn(DETAILS['payment']['cardNumber'], json.dumps(shipment))

    def test_preview_shortage_and_price_conflict_do_not_pay(self):
        self.call([{'id': 0, 'quantity': 1}], preview=True)
        self.call([{'id': 0, 'quantity': 99}])
        self.call([{'id': 0, 'quantity': 1}], expectedTotal=999)
        self.process_payment.assert_not_called()
        self.publish_shipping.assert_not_called()

    def test_inventory_failure_prevents_payment(self):
        self.fetch_inventory.side_effect = TimeoutError()
        self.assertEqual(self.call([{'id': 0, 'quantity': 1}])[0], 502)
        self.process_payment.assert_not_called()
        self.assertEqual(self.order_count(), 0)

    def test_inventory_api_called_for_distinct_ids(self):
        self.call([{'id': 0, 'quantity': 1}, {'id': 0, 'quantity': 2}])
        self.fetch_inventory.assert_called_once_with({0})

    def test_real_http_inventory_client_handles_missing_item(self):
        from urllib.error import HTTPError
        with patch.dict(os.environ, {'INVENTORY_ITEM_URL_TEMPLATE': 'https://example.test/items/{id}'}), \
             patch.object(lambda_function, 'http_json', side_effect=[PRODUCT, HTTPError('url', 404, 'missing', {}, None)]) as http:
            self.assertEqual(fetch_inventory_original({0, 9}), [PRODUCT])
            self.assertEqual(http.call_args_list[0].args[0], 'https://example.test/items/0')

    def test_payment_client_checks_response_and_uses_post_payload(self):
        with patch.dict(os.environ, {'PAYMENT_URL': 'https://example.test/payment'}), \
             patch.object(lambda_function, 'http_json', return_value={'paymentToken': 'PAY-real'}) as http:
            self.assertEqual(process_payment_original(DETAILS['payment'], 1.25, 'CS-1'), 'PAY-real')
            self.assertEqual(http.call_args.args[1]['amount'], 1.25)
            http.return_value = {}
            with self.assertRaises(lambda_function.ServiceError):
                process_payment_original(DETAILS['payment'], 1.25, 'CS-1')

    def test_publisher_uses_eventbridge_and_checks_failed_entries(self):
        sdk = MagicMock()
        client = sdk.client.return_value
        client.put_events.return_value = {'FailedEntryCount': 0, 'Entries': [{'EventId': 'event-1'}]}
        shipment = {'shipmentRequestId': 'CS-test'}
        with patch.object(lambda_function, 'boto3', sdk), \
             patch.dict(sys.modules, {'botocore': MagicMock(), 'botocore.config': MagicMock()}):
            publish_shipping_original(shipment)
            entry = client.put_events.call_args.kwargs['Entries'][0]
            self.assertEqual(entry['Source'], 'clothingstore.orders')
            self.assertEqual(entry['DetailType'], 'ShippingRequested')
            self.assertEqual(json.loads(entry['Detail']), shipment)
            client.put_events.return_value = {'FailedEntryCount': 1, 'Entries': [{'ErrorCode': 'InternalFailure'}]}
            with self.assertRaises(lambda_function.ServiceError):
                publish_shipping_original(shipment)

    def test_http_client_encodes_json_post_and_has_timeout(self):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b'{"paymentToken":"PAY-http"}'
        with patch.object(lambda_function, 'urlopen', return_value=response) as opened:
            self.assertEqual(lambda_function.http_json('https://example.test/payment', {'amount': 1}),
                             {'paymentToken': 'PAY-http'})
        request = opened.call_args.args[0]
        self.assertEqual(request.get_method(), 'POST')
        self.assertEqual(json.loads(request.data), {'amount': 1})
        self.assertEqual(opened.call_args.kwargs['timeout'], 3)
        with self.assertRaises(lambda_function.ServiceError):
            lambda_function.http_json('http://example.test/payment')

    def test_missing_address_prevents_payment_and_full_card_is_not_logged(self):
        self.assertEqual(self.call([{'id': 0, 'quantity': 1}], shipping={'fullName': 'Test'})[0], 400)
        self.process_payment.assert_not_called()
        self.process_payment.side_effect = OSError(DETAILS['payment']['cardNumber'])
        with patch('builtins.print') as logged:
            self.assertEqual(self.call([{'id': 0, 'quantity': 1}])[0], 502)
        self.assertNotIn(DETAILS['payment']['cardNumber'], str(logged.call_args))

    def test_options_bad_json_and_method(self):
        self.assertEqual(lambda_handler({'httpMethod': 'OPTIONS'}, None)['statusCode'], 204)
        self.assertEqual(lambda_handler({'body': '{not json'}, None)['statusCode'], 400)
        self.assertEqual(lambda_handler({'httpMethod': 'GET'}, None)['statusCode'], 405)


if __name__ == '__main__':
    unittest.main()

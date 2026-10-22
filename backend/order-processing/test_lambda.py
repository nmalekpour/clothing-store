"""Run: python3 backend/order-processing/test_lambda.py"""
import json
import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(__file__))
from lambda_function import lambda_handler


INVENTORY = [
    {'id': 0, 'availableQty': 12},
    {'id': 1, 'availableQty': 2},
]
ORDER_DETAILS = {
    'payment': {'cardNumber': '4111111111111111'},
    'shipping': {'fullName': 'Jane Doe', 'city': 'Columbus'},
}


class InventoryResponse:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(INVENTORY).encode('utf-8')


def call(order):
    event = {'body': json.dumps(order)}
    with patch('lambda_function.urlopen', return_value=InventoryResponse()):
        response = lambda_handler(event, None)
    assert response['headers']['Access-Control-Allow-Origin'] == '*'
    return response['statusCode'], json.loads(response['body'])


status, body = call({**ORDER_DETAILS, 'items': [{'id': 0, 'quantity': 2}]})
assert status == 200 and body['confirmationNumber'].startswith('CS-')

status, body = call({**ORDER_DETAILS, 'items': [{'id': 1, 'quantity': 3}]})
assert status == 409
assert body['unavailable'] == [{'id': 1, 'requestedQty': 3, 'availableQty': 2}]

status, body = call({**ORDER_DETAILS, 'items': [{'id': 99, 'quantity': 1}]})
assert status == 409
assert body['unavailable'] == [{'id': 99, 'requestedQty': 1, 'availableQty': 0}]

status, body = call({'items': []})
assert status == 400 and 'error' in body

status, body = lambda_handler({'body': '{not json'}, None)['statusCode'], None
assert status == 400

status, body = lambda_handler({'httpMethod': 'OPTIONS'}, None)['statusCode'], None
assert status == 204

print('all order-processing tests passed')
"""Run: python3 -B backend/inventory/test_lambda.py"""
import json
import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import lambda_function
from lambda_function import lambda_handler
from test_db import Connection

BASE = '/inventory-management/inventory'
db = Connection()


def call(resource, path=None, query=None):
    with patch('lambda_function.connect', return_value=db):
        res = lambda_handler({'resource': resource, 'pathParameters': path, 'queryStringParameters': query}, None)
    assert res['headers']['Access-Control-Allow-Origin'] == '*'
    return res['statusCode'], json.loads(res['body'])


status, body = call(BASE)
assert status == 200 and len(body) == 5
assert set(body[0]) == {'id', 'name', 'price', 'description', 'image', 'availableQty'}
assert body[0] == {'id': 0, 'name': 'Sage Dress', 'price': 280.0, 'availableQty': 12,
                   'description': 'Flowing midi dress in soft sage linen.', 'image': '/images/sage-dress.jpeg'}
assert [i['id'] for i in body] == [0, 1, 2, 3, 4]

assert call(BASE + '/items/{id}', {'id': '2'}) == (200, body[2])
assert call(BASE + '/items/{id}', {'id': '99'})[0] == 404
assert call(BASE + '/items/{id}', {'id': 'abc'})[0] == 400

status, hits = call(BASE + '/items', query={'name': 'dress'})
assert status == 200 and [i['id'] for i in hits] == [0]
assert call(BASE + '/items', query={'name': 'DRESS'})[1] == hits
assert call(BASE + '/items', query={'name': 'nope'}) == (200, [])
assert call(BASE + '/items', query={'name': '%'}) == (200, [])
assert call(BASE + '/items')[0] == 400

# Missing connection settings must surface as a service error, not a crash.
with patch.dict(os.environ, {}, clear=True), patch.object(lambda_function, '_connection', None):
    assert lambda_handler({'resource': BASE}, None)['statusCode'] == 503

db.close()
print('all inventory tests passed')

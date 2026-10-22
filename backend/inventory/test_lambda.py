"""Run: python3 backend/inventory/test_lambda.py"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from lambda_function import lambda_handler

BASE = '/inventory-management/inventory'


def call(resource, path=None, query=None):
    res = lambda_handler({'resource': resource, 'pathParameters': path, 'queryStringParameters': query}, None)
    assert res['headers']['Access-Control-Allow-Origin'] == '*'
    return res['statusCode'], json.loads(res['body'])


status, body = call(BASE)
assert status == 200 and len(body) == 5
assert set(body[0]) == {'id', 'name', 'price', 'description', 'image', 'availableQty'}

assert call(BASE + '/items/{id}', {'id': '2'}) == (200, body[2])
assert call(BASE + '/items/{id}', {'id': '99'})[0] == 404
assert call(BASE + '/items/{id}', {'id': 'abc'})[0] == 400

status, hits = call(BASE + '/items', query={'name': 'dress'})
assert status == 200 and [i['id'] for i in hits] == [0]
assert call(BASE + '/items', query={'name': 'nope'}) == (200, [])
assert call(BASE + '/items')[0] == 400

print('all inventory tests passed')

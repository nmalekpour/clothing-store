"""Live Lab 7 smoke test. Runs previews and lab orders with synthetic test details."""
import argparse
import json
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='https://xnigucru41.execute-api.us-east-2.amazonaws.com/dev')
    args = parser.parse_args()

    def call(path, payload=None, method=None, headers=None):
        body = json.dumps(payload).encode() if payload is not None else None
        request = Request(args.base_url.rstrip('/') + path, data=body,
                          method=method or ('POST' if body is not None else 'GET'),
                          headers={'Content-Type': 'application/json', 'Origin': 'http://localhost:5173', **(headers or {})})
        try:
            response = urlopen(request, timeout=30)
        except HTTPError as error:
            response = error
        with response:
            raw = response.read()
            assert response.headers.get('Access-Control-Allow-Origin') in ('*', 'http://localhost:5173'), 'Missing CORS header'
            return response.status, json.loads(raw) if raw else {}

    inventory_path = '/inventory-management/inventory'
    order_path = '/order-processing/order'
    status, catalog = call(inventory_path)
    assert status == 200 and isinstance(catalog, list) and catalog, 'Inventory GET failed'
    product = next(item for item in catalog if item['availableQty'] >= 2)
    item_id, stock = product['id'], product['availableQty']
    status, item = call(f'{inventory_path}/items/{item_id}')
    assert status == 200 and item['id'] == item_id, 'Inventory ID lookup failed'
    status, matches = call(f"{inventory_path}/items?name={quote(product['name'])}")
    assert status == 200 and any(match['id'] == item_id for match in matches), 'Inventory name lookup failed'
    print('PASS: inventory list, ID and name lookups')

    for path, method in [(inventory_path, 'GET'), (order_path, 'POST')]:
        status, _ = call(path, method='OPTIONS', headers={'Access-Control-Request-Method': method, 'Access-Control-Request-Headers': 'content-type'})
        assert status in (200, 204), 'CORS preflight failed'
    print('PASS: inventory and order CORS')

    items = [{'id': item_id, 'quantity': 1}]
    status, preview = call(order_path, {'preview': True, 'items': items})
    assert status == 200 and 'confirmationNumber' not in preview and 'total' in preview, 'New price-preview backend is not deployed'
    assert preview['itemCount'] == 1 and preview['items'][0]['quantity'] == 1
    print('PASS: preview returns server prices without creating a confirmation')

    details = {'payment': {'cardholderName': 'Lab API Test', 'cardNumber': '4111111111111111',
                           'expirationDate': '12/30', 'cvv': '123'},
               'shipping': {'fullName': 'Lab API Test', 'address': '1 Main St',
                            'city': 'Columbus', 'state': 'OH', 'zip': '43210'}}
    status, shortage = call(order_path, {**details, 'items': [{'id': item_id, 'quantity': stock}, {'id': item_id, 'quantity': 1}]})
    assert status == 409 and 'confirmationNumber' not in shortage, 'Duplicate IDs bypass stock check'
    assert shortage['unavailable'] == [{'id': item_id, 'requestedQty': stock + 1, 'availableQty': stock}]
    print('PASS: duplicate item quantities are combined before stock validation')

    status, changed = call(order_path, {**details, 'items': items, 'expectedTotal': preview['total'] + 1})
    assert status == 409 and changed.get('priceChanged') is True, 'Changed-price confirmation was accepted'
    status, invalid = call(order_path, {'items': items, 'payment': {}, 'shipping': {}})
    assert status == 400 and 'error' in invalid
    print('PASS: changed prices and missing payment/shipping are rejected')

    status, confirmed = call(order_path, {**details, 'items': items, 'expectedTotal': preview['total']})
    assert status == 200 and confirmed.get('confirmationNumber'), 'Normal order failed'
    assert confirmed['total'] == preview['total'] and confirmed['items'] == preview['items']
    print('PASS: order returns backend confirmation and matching authoritative total')


if __name__ == '__main__':
    main()

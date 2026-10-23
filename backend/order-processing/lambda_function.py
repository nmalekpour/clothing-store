"""Order processing and non-mutating price previews through one POST endpoint."""
import json
import os
import uuid
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from urllib.request import Request, urlopen

BASE_URL = 'https://xnigucru41.execute-api.us-east-2.amazonaws.com/dev'
INVENTORY_URL = os.environ.get('INVENTORY_URL', f'{BASE_URL}/inventory-management/inventory')
HEADERS = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'POST,OPTIONS',
}


def respond(status, body):
    return {'statusCode': status, 'headers': HEADERS, 'body': json.dumps(body)}


def inventory_items():
    with urlopen(Request(INVENTORY_URL, method='GET'), timeout=10) as response:
        if response.status != 200:
            raise RuntimeError('inventory service returned an error')
        payload = json.loads(response.read().decode('utf-8'))
    if not isinstance(payload, list):
        raise RuntimeError('inventory service returned invalid data')
    return payload


def validate_order(order):
    if not isinstance(order, dict):
        return 'request body must be a JSON object'
    if 'preview' in order and not isinstance(order['preview'], bool):
        return 'preview must be a boolean'
    preview = order.get('preview', False)
    items = order.get('items')
    if not isinstance(items, list) or (not items and not preview):
        return 'items must be a non-empty list'
    if not preview:
        if not isinstance(order.get('payment'), dict) or not order['payment']:
            return 'payment must be a non-empty object'
        if not isinstance(order.get('shipping'), dict) or not order['shipping']:
            return 'shipping must be a non-empty object'
    for item in items:
        if not isinstance(item, dict):
            return 'each item must be an object'
        if type(item.get('id')) is not int or item['id'] < 0:
            return 'each item id must be a non-negative integer'
        if type(item.get('quantity')) is not int or item['quantity'] <= 0:
            return 'each item quantity must be a positive integer'
    if 'expectedTotal' in order:
        try:
            money(order['expectedTotal'])
        except (ValueError, InvalidOperation):
            return 'expectedTotal must be a non-negative monetary amount'
    return None


def money(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError('invalid price')
    amount = Decimal(str(value))
    if not amount.is_finite() or amount < 0:
        raise ValueError('invalid price')
    return amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def price_order(requested_items, inventory):
    quantities = {}
    for item in requested_items:
        quantities[item['id']] = quantities.get(item['id'], 0) + item['quantity']
    catalog = {}
    for product in inventory:
        if not isinstance(product, dict) or type(product.get('id')) is not int or product['id'] in catalog:
            raise ValueError('invalid inventory')
        catalog[product['id']] = product
    items, unavailable = [], []
    total = Decimal('0.00')
    for item_id, quantity in quantities.items():
        product = catalog.get(item_id)
        available = product.get('availableQty', 0) if product else 0
        if type(available) is not int or available < 0:
            raise ValueError('invalid inventory quantity')
        if quantity > available:
            unavailable.append({'id': item_id, 'requestedQty': quantity, 'availableQty': available})
        if product is None:
            continue
        if any(not isinstance(product.get(field), str) for field in ('name', 'description', 'image')):
            raise ValueError('invalid inventory product')
        price = money(product.get('price'))
        subtotal = price * quantity
        total += subtotal
        items.append({**product, 'price': float(price), 'quantity': quantity, 'subtotal': float(subtotal)})
    return {'items': items, 'total': float(total), 'itemCount': sum(quantities.values()), 'unavailable': unavailable}


def lambda_handler(event, context):
    event = event or {}
    method = event.get('httpMethod') or (event.get('requestContext') or {}).get('http', {}).get('method')
    if method == 'OPTIONS':
        return respond(204, {})
    if method and method != 'POST':
        return respond(405, {'error': 'method not allowed'})
    try:
        order = json.loads(event.get('body') or '')
    except (TypeError, json.JSONDecodeError):
        return respond(400, {'error': 'request body must be valid JSON'})
    validation_error = validate_order(order)
    if validation_error:
        return respond(400, {'error': validation_error})
    try:
        quote = price_order(order['items'], inventory_items())
    except (OSError, RuntimeError, ValueError, InvalidOperation, OverflowError):
        return respond(502, {'error': 'inventory service is unavailable or returned invalid data'})
    # A preview never creates a confirmation, even for an empty or unavailable bag.
    if order.get('preview', False):
        return respond(200, quote)
    if quote['unavailable']:
        return respond(409, {'error': 'one or more items are unavailable', 'unavailable': quote['unavailable']})
    if 'expectedTotal' in order and money(order['expectedTotal']) != money(quote['total']):
        return respond(409, {'error': 'Prices have changed. Review the updated total before confirming.', 'priceChanged': True, 'unavailable': []})
    return respond(200, {**quote, 'confirmationNumber': f'CS-{uuid.uuid4().hex[:8].upper()}'})

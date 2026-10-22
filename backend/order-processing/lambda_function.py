"""Order-processing Lambda for API Gateway proxy integration."""
import json
from urllib.request import Request, urlopen


BASE_URL = 'https://xnigucru41.execute-api.us-east-2.amazonaws.com/dev'
INVENTORY_URL = f'{BASE_URL}/inventory-management/inventory'

HEADERS = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'POST,OPTIONS',
}


def respond(status, body):
    return {'statusCode': status, 'headers': HEADERS, 'body': json.dumps(body)}


def inventory_items():
    request = Request(INVENTORY_URL, method='GET')
    with urlopen(request, timeout=10) as response:
        if response.status != 200:
            raise RuntimeError('inventory service returned an error')
        payload = json.loads(response.read().decode('utf-8'))
    if not isinstance(payload, list):
        raise RuntimeError('inventory service returned invalid data')
    return payload


def validate_order(order):
    if not isinstance(order, dict):
        return 'request body must be a JSON object'

    items = order.get('items')
    if not isinstance(items, list) or not items:
        return 'items must be a non-empty list'
    if not isinstance(order.get('payment'), dict) or not order['payment']:
        return 'payment must be a non-empty object'
    if not isinstance(order.get('shipping'), dict) or not order['shipping']:
        return 'shipping must be a non-empty object'

    for item in items:
        if not isinstance(item, dict):
            return 'each item must be an object'
        item_id = item.get('id')
        quantity = item.get('quantity')
        if isinstance(item_id, bool) or not isinstance(item_id, int):
            return 'each item id must be an integer'
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            return 'each item quantity must be a positive integer'
    return None


def lambda_handler(event, context):
    event = event or {}
    if (event.get('requestContext') or {}).get('http', {}).get('method') == 'OPTIONS' \
            or event.get('httpMethod') == 'OPTIONS':
        return respond(204, {})

    body = event.get('body')
    if not isinstance(body, str):
        return respond(400, {'error': 'request body is required'})
    try:
        order = json.loads(body)
    except (TypeError, json.JSONDecodeError):
        return respond(400, {'error': 'request body must be valid JSON'})

    validation_error = validate_order(order)
    if validation_error:
        return respond(400, {'error': validation_error})

    try:
        inventory = {item.get('id'): item for item in inventory_items()}
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError):
        return respond(502, {'error': 'inventory service is unavailable'})

    unavailable = []
    for requested in order['items']:
        available = inventory.get(requested['id'], {}).get('availableQty', 0)
        if not isinstance(available, int) or requested['quantity'] > available:
            unavailable.append({
                'id': requested['id'],
                'requestedQty': requested['quantity'],
                'availableQty': available if isinstance(available, int) else 0,
            })

    if unavailable:
        return respond(409, {
            'error': 'one or more items are unavailable',
            'unavailable': unavailable,
        })

    confirmation = f'CS-{__import__("uuid").uuid4().hex[:8].upper()}'
    return respond(200, {'confirmationNumber': confirmation})
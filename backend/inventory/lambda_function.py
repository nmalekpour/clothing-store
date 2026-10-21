"""inventory-management Lambda (Python 3.12, API Gateway REST API w/ Lambda proxy integration).

Routes (all GET, all pointed at this one function):
  /inventory-management/inventory              -> every item
  /inventory-management/inventory/items/{id}   -> one item, 404 if missing
  /inventory-management/inventory/items?name=  -> items whose name contains `name` (case-insensitive)
"""
import json

# Image paths are served by the frontend (public/images/), not by this service.
INVENTORY = [
    {'id': 0, 'name': 'Sage Dress', 'price': 280.00, 'availableQty': 12,
     'description': 'Flowing midi dress in soft sage linen.', 'image': '/images/sage-dress.jpeg'},
    {'id': 1, 'name': 'White Tank', 'price': 90.00, 'availableQty': 40,
     'description': 'Ribbed cotton tank, an everyday essential.', 'image': '/images/white-tank.jpeg'},
    {'id': 2, 'name': 'Peacoat', 'price': 550.00, 'availableQty': 5,
     'description': 'Double-breasted wool peacoat.', 'image': '/images/coat.jpeg'},
    {'id': 3, 'name': 'Wide-Leg Pants', 'price': 148.00, 'availableQty': 20,
     'description': 'High-waisted trousers with a relaxed wide leg.', 'image': '/images/pants.png'},
    {'id': 4, 'name': 'Diamond Lariat Necklace', 'price': 1200.00, 'availableQty': 2,
     'description': 'Delicate lariat chain with a diamond drop.', 'image': '/images/necklace.png'},
]

# With proxy integration, API Gateway's "Enable CORS" only covers the OPTIONS preflight;
# the actual GET response must carry the header itself.
HEADERS = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'GET,OPTIONS',
}


def respond(status, body):
    return {'statusCode': status, 'headers': HEADERS, 'body': json.dumps(body)}


def lambda_handler(event, context):
    resource = event.get('resource') or ''
    path_params = event.get('pathParameters') or {}
    query = event.get('queryStringParameters') or {}

    if resource.endswith('/items/{id}'):
        try:
            item_id = int(path_params.get('id'))
        except (TypeError, ValueError):
            return respond(400, {'error': 'id must be an integer'})
        item = next((i for i in INVENTORY if i['id'] == item_id), None)
        if item is None:
            return respond(404, {'error': f'item {item_id} not found'})
        return respond(200, item)

    if resource.endswith('/items'):
        name = (query.get('name') or '').strip().lower()
        if not name:
            return respond(400, {'error': 'name query parameter is required'})
        return respond(200, [i for i in INVENTORY if name in i['name'].lower()])

    return respond(200, INVENTORY)

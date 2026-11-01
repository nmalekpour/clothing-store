"""inventory-management Lambda (Python 3.12, API Gateway REST API w/ Lambda proxy integration).

Routes (all GET, all pointed at this one function):
  /inventory-management/inventory              -> every item
  /inventory-management/inventory/items/{id}   -> one item, 404 if missing
  /inventory-management/inventory/items?name=  -> items whose name contains `name` (case-insensitive)

Items come from the ITEM table in MySQL (backend/db/schema.sql). ITEM_NUMBER is the public `id`.
Connection settings come from the DB_HOST, DB_USER, DB_PASSWORD and DB_NAME environment variables.
"""
import json
import os

try:
    import pymysql
    DB_ERRORS = (pymysql.MySQLError,)
except ImportError:  # Lets the tests run without the driver installed.
    pymysql = None
    DB_ERRORS = ()

# With proxy integration, API Gateway's "Enable CORS" only covers the OPTIONS preflight;
# the actual GET response must carry the header itself.
HEADERS = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'GET,OPTIONS',
}

ITEM_COLUMNS = 'ITEM_NUMBER, NAME, DESCRIPTION, AVAILABLE_QUANTITY, UNIT_PRICE, IMAGE'

CA_BUNDLE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rds-ca.pem')

# Reused across warm invocations.
_connection = None


def connect():
    global _connection
    if _connection is None or not _connection.open:
        settings = {'host': os.environ['DB_HOST'], 'user': os.environ['DB_USER'],
                    'password': os.environ['DB_PASSWORD'], 'database': os.environ.get('DB_NAME', 'clothingstore'),
                    'port': int(os.environ.get('DB_PORT', '3306'))}
        # TLS verified against the bundled RDS CA (backend/db/rds-ca.pem), which also lets pymysql use
        # MySQL 8's caching_sha2_password login without extra crypto libraries.
        _connection = pymysql.connect(**settings, connect_timeout=5, autocommit=True, ssl_ca=CA_BUNDLE,
                                      ssl_verify_cert=True, ssl_verify_identity=True)
    return _connection


def to_item(row):
    number, name, description, quantity, price, image = row
    return {'id': number, 'name': name, 'price': float(price), 'availableQty': quantity,
            'description': description or '', 'image': image or ''}


def query_items(where='', params=()):
    with connect().cursor() as cursor:
        cursor.execute(f'SELECT {ITEM_COLUMNS} FROM ITEM {where} ORDER BY ITEM_NUMBER', params)
        return [to_item(row) for row in cursor.fetchall()]


def respond(status, body):
    return {'statusCode': status, 'headers': HEADERS, 'body': json.dumps(body)}


def lambda_handler(event, context):
    resource = event.get('resource') or ''
    path_params = event.get('pathParameters') or {}
    query = event.get('queryStringParameters') or {}

    try:
        if resource.endswith('/items/{id}'):
            try:
                item_id = int(path_params.get('id'))
            except (TypeError, ValueError):
                return respond(400, {'error': 'id must be an integer'})
            items = query_items('WHERE ITEM_NUMBER = %s', (item_id,))
            if not items:
                return respond(404, {'error': f'item {item_id} not found'})
            return respond(200, items[0])

        if resource.endswith('/items'):
            name = (query.get('name') or '').strip().lower()
            if not name:
                return respond(400, {'error': 'name query parameter is required'})
            # Escape LIKE wildcards so the search stays a plain substring match.
            pattern = '%' + name.replace('!', '!!').replace('%', '!%').replace('_', '!_') + '%'
            return respond(200, query_items("WHERE LOWER(NAME) LIKE %s ESCAPE '!'", (pattern,)))

        return respond(200, query_items())
    except (KeyError, *DB_ERRORS) as error:
        # The cause goes to CloudWatch only; a KeyError names the missing environment variable.
        print(f'inventory database error: {error!r}')
        return respond(503, {'error': 'inventory database is unavailable'})

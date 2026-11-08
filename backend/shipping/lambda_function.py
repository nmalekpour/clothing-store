"""Independent shipping initiation via API Gateway or SNS-wrapped EventBridge events."""
import json
import os
import uuid
from decimal import Decimal

try:
    import pymysql
    DB_ERRORS = (pymysql.MySQLError,)
except ImportError:
    pymysql = None
    DB_ERRORS = ()

HEADERS = {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*',
           'Access-Control-Allow-Headers': 'Content-Type', 'Access-Control-Allow-Methods': 'POST,OPTIONS'}


def respond(status, body):
    return {'statusCode': status, 'headers': HEADERS, 'body': json.dumps(body)}


def required_text(data, field, maximum=255):
    value = data.get(field)
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f'{field} is required and must be at most {maximum} characters')
    return value.strip()


CA_BUNDLE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rds-ca.pem')

# Reused across warm invocations.
_connection = None


def connect():
    global _connection
    if _connection is None or not _connection.open:
        settings = {'host': os.environ['DB_HOST'], 'user': os.environ['DB_USER'],
                    'password': os.environ['DB_PASSWORD'], 'database': os.environ.get('DB_NAME', 'shippingdb'),
                    'port': int(os.environ.get('DB_PORT', '3306'))}
        # TLS verified against the bundled RDS CA (backend/db/rds-ca.pem), which also lets pymysql use
        # MySQL 8's caching_sha2_password login without extra crypto libraries.
        _connection = pymysql.connect(**settings, connect_timeout=5, autocommit=True, ssl_ca=CA_BUNDLE,
                                      ssl_verify_cert=True, ssl_verify_identity=True, read_timeout=5, write_timeout=5)
    return _connection



def validate_shipment(body):
    if not isinstance(body, dict):
        raise ValueError('shipment must be an object')
    required_text(body, 'shipmentRequestId', 64)
    required_text(body, 'businessId', 64)
    address = body.get('shipmentAddress')
    if not isinstance(address, dict):
        raise ValueError('shipmentAddress must be an object')
    for field in ('fullName', 'address', 'city', 'state', 'zip'):
        required_text(address, field)
    count, weights = body.get('packetCount'), body.get('packetWeightsLb')
    if type(count) is not int or count <= 0 or not isinstance(weights, list) or len(weights) != count:
        raise ValueError('packetCount must be positive and match packetWeightsLb')
    for weight in weights:
        if isinstance(weight, bool) or not isinstance(weight, (int, float)):
            raise ValueError('packet weights must be positive finite numbers')
        number = Decimal(str(weight))
        if not number.is_finite() or number <= 0:
            raise ValueError('packet weights must be positive finite numbers')
    # Reject non-JSON numbers anywhere in the address before attempting persistence.
    json.dumps(body, allow_nan=False)
    return body


def save_shipment(body):
    """INSERT IGNORE plus a unique key makes concurrent SNS deliveries idempotent."""
    token = f'SHIP-{uuid.uuid4().hex}'
    with connect().cursor() as cursor:
        cursor.execute('INSERT IGNORE INTO SHIPMENT (SHIPPING_TOKEN, SHIPMENT_REQUEST_ID, BUSINESS_ID, '
                       'ADDRESS_JSON, PACKET_COUNT, WEIGHTS_JSON) VALUES (%s, %s, %s, %s, %s, %s)',
                       (token, body['shipmentRequestId'], body['businessId'],
                        json.dumps(body['shipmentAddress'], allow_nan=False), body['packetCount'],
                        json.dumps(body['packetWeightsLb'], allow_nan=False)))
        cursor.execute('SELECT SHIPPING_TOKEN FROM SHIPMENT WHERE SHIPMENT_REQUEST_ID = %s',
                       (body['shipmentRequestId'],))
        row = cursor.fetchone()
        if not row:
            raise RuntimeError('shipment was not saved')
        return row[0]


def lambda_handler(event, context):
    event = event or {}
    if 'Records' in event:
        # Raise on malformed events or database failures so Lambda retries, never return HTTP 200.
        for record in event['Records']:
            envelope = json.loads(record['Sns']['Message'])
            if envelope.get('source') != 'clothingstore.orders' or envelope.get('detail-type') != 'ShippingRequested':
                raise ValueError('unexpected shipping event')
            save_shipment(validate_shipment(envelope['detail']))
        return {'processed': len(event['Records'])}
    method = event.get('httpMethod') or (event.get('requestContext') or {}).get('http', {}).get('method')
    if method == 'OPTIONS':
        return respond(204, {})
    if method and method != 'POST':
        return respond(405, {'error': 'method not allowed'})
    try:
        body = validate_shipment(json.loads(event.get('body') or ''))
    except (ValueError, TypeError) as error:
        return respond(400, {'error': str(error) if not isinstance(error, json.JSONDecodeError) else 'invalid JSON'})
    try:
        return respond(200, {'shippingToken': save_shipment(body)})
    except (KeyError, OSError, RuntimeError, *DB_ERRORS) as error:
        print(json.dumps({'event': 'shipping_failed', 'errorType': type(error).__name__}))
        return respond(502, {'error': 'shipping database is unavailable'})

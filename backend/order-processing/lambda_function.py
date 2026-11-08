"""Lab integration: HTTP inventory/payment, token-only orders, EventBridge shipping."""
import json
import os
import uuid
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from urllib.request import Request, urlopen
from urllib.error import HTTPError

try:
    import boto3
except ImportError:  # Local unit tests mock the publisher.
    boto3 = None

try:
    import pymysql
    DB_ERRORS = (pymysql.MySQLError,)
except ImportError:  # Lets the tests run without the driver installed.
    pymysql = None
    DB_ERRORS = ()

HEADERS = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'POST,OPTIONS',
}


def respond(status, body):
    return {'statusCode': status, 'headers': HEADERS, 'body': json.dumps(body)}


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
                                      ssl_verify_cert=True, ssl_verify_identity=True, read_timeout=5, write_timeout=5)
    return _connection


def load_inventory(cursor, item_ids, lock=False):
    """Requested ITEM rows in the inventory API's shape; `lock` holds them until the transaction ends."""
    if not item_ids:
        return []
    placeholders = ', '.join(['%s'] * len(item_ids))
    cursor.execute(
        'SELECT ITEM_NUMBER, NAME, DESCRIPTION, AVAILABLE_QUANTITY, UNIT_PRICE, IMAGE FROM ITEM '
        f'WHERE ITEM_NUMBER IN ({placeholders}) ORDER BY ITEM_NUMBER' + (' FOR UPDATE' if lock else ''),
        sorted(item_ids))
    # price_order validates the raw values, so a NULL or bad price fails the request instead of crashing.
    return [{'id': number, 'name': name, 'price': price, 'availableQty': quantity,
             'description': description or '', 'image': image or ''}
            for number, name, description, quantity, price, image in cursor.fetchall()]


def text(details, field):
    value = details.get(field)
    return (value.strip() or None) if isinstance(value, str) else None


def save_order(cursor, order, quote, confirmation, payment_token):
    shipping = order['shipping']
    cursor.execute(
        'INSERT INTO SHIPPING_INFO (NAME, ADDRESS1, ADDRESS2, CITY, STATE, COUNTRY, POSTAL_CODE, EMAIL) '
        'VALUES (%s, %s, %s, %s, %s, %s, %s, %s)',
        (text(shipping, 'fullName'), text(shipping, 'address'), text(shipping, 'apartment'), text(shipping, 'city'),
         text(shipping, 'state'), text(shipping, 'country'), text(shipping, 'zip'), text(shipping, 'email')))
    shipping_id = cursor.lastrowid
    cursor.execute(
        'INSERT INTO CUSTOMER_ORDER (CONFIRMATION_NUMBER, CUSTOMER_NAME, CUSTOMER_EMAIL, SHIPPING_INFO_ID_FK, '
        'PAYMENT_TOKEN, TOTAL) VALUES (%s, %s, %s, %s, %s, %s)',
        (confirmation, text(shipping, 'fullName'), text(shipping, 'email'), shipping_id, payment_token, quote['total']))
    order_id = cursor.lastrowid
    cursor.executemany(
        'INSERT INTO CUSTOMER_ORDER_LINE_ITEM (ITEM_ID, ITEM_NAME, QUANTITY, UNIT_PRICE, CUSTOMER_ORDER_ID_FK) '
        'VALUES (%s, %s, %s, %s, %s)',
        [(item['id'], item['name'], item['quantity'], item['price'], order_id) for item in quote['items']])
    cursor.executemany(
        'UPDATE ITEM SET AVAILABLE_QUANTITY = AVAILABLE_QUANTITY - %s WHERE ITEM_NUMBER = %s',
        [(item['quantity'], item['id']) for item in quote['items']])


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
        for field in ('fullName', 'address', 'city', 'state', 'zip'):
            value = order['shipping'].get(field)
            if not isinstance(value, str) or not value.strip() or len(value) > 255:
                return f'shipping {field} is required and must be at most 255 characters'
        for field in ('apartment', 'country', 'email'):
            value = order['shipping'].get(field)
            if value is not None and (not isinstance(value, str) or len(value) > 255):
                return f'shipping {field} must be a string of at most 255 characters'
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


class ServiceError(Exception):
    """An upstream failure with a safe, local message (never an upstream body)."""


class PaymentRejected(ServiceError):
    pass


def http_json(url, payload=None):
    if not url.startswith('https://'):
        raise ServiceError('service URL must use HTTPS')
    data = json.dumps(payload, allow_nan=False).encode() if payload is not None else None
    request = Request(url, data=data, headers={'Content-Type': 'application/json'})
    with urlopen(request, timeout=3) as response:
        return json.loads(response.read())


def fetch_inventory(item_ids):
    inventory = []
    if not item_ids:
        return inventory
    template = os.environ['INVENTORY_ITEM_URL_TEMPLATE']
    if '{id}' not in template:
        raise ServiceError('inventory URL must contain {id}')
    for item_id in sorted(item_ids):
        try:
            product = http_json(template.format(id=item_id))
        except HTTPError as error:
            if error.code == 404:
                continue  # price_order reports this as unavailable.
            raise ServiceError('inventory service is unavailable') from None
        if not isinstance(product, dict) or product.get('id') != item_id:
            raise ServiceError('inventory service returned an unexpected item')
        inventory.append(product)
    return inventory


def process_payment(payment, total, confirmation):
    try:
        result = http_json(os.environ['PAYMENT_URL'], {
            'amount': total, 'orderReference': confirmation, 'payment': payment,
        })
    except HTTPError as error:
        if error.code in (400, 402, 422):
            raise PaymentRejected('payment was rejected; check the payment information') from None
        raise ServiceError('payment service is unavailable') from None
    token = result.get('paymentToken') if isinstance(result, dict) else None
    if not isinstance(token, str) or not token.strip() or len(token) > 64:
        raise ServiceError('payment service returned an invalid token')
    return token


def shipping_request(order, quote, confirmation):
    return {
        'shipmentRequestId': confirmation,
        'businessId': os.environ['BUSINESS_ID'],
        'shipmentAddress': {field: text(order['shipping'], field)
                            for field in ('fullName', 'address', 'apartment', 'city', 'state', 'zip', 'country', 'email')
                            if text(order['shipping'], field) is not None},
        'packetCount': len(quote['items']),
        'packetWeightsLb': [float(item['quantity']) for item in quote['items']],
    }


def publish_shipping(shipment):
    if boto3 is None:
        raise ServiceError('AWS SDK is unavailable')
    from botocore.config import Config
    client = boto3.client('events', config=Config(
        connect_timeout=2, read_timeout=2, retries={'total_max_attempts': 1}))
    result = client.put_events(Entries=[{
        'EventBusName': os.environ['EVENT_BUS_NAME'],
        'Source': 'clothingstore.orders',
        'DetailType': 'ShippingRequested',
        'Detail': json.dumps(shipment, allow_nan=False),
    }])
    if result.get('FailedEntryCount') != 0 or not result.get('Entries', [{}])[0].get('EventId'):
        raise ServiceError('EventBridge did not accept the shipping event')


def check_quote(order, quote):
    if quote['unavailable']:
        return respond(409, {'error': 'one or more items are unavailable', 'unavailable': quote['unavailable']})
    if 'expectedTotal' in order and money(order['expectedTotal']) != money(quote['total']):
        return respond(409, {'error': 'Prices have changed. Review the updated total before confirming.',
                             'priceChanged': True, 'unavailable': []})
    return None


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
    item_ids = {item['id'] for item in order['items']}
    payment_token = None
    confirmation = None
    try:
        quote = price_order(order['items'], fetch_inventory(item_ids))
        if order.get('preview', False):
            return respond(200, quote)
        error_response = check_quote(order, quote)
        if error_response:
            return error_response
        # Fail missing configuration before taking payment.
        if not os.environ['EVENT_BUS_NAME'].strip() or not os.environ['BUSINESS_ID'].strip() or len(os.environ['BUSINESS_ID']) > 64:
            raise ServiceError('shipping configuration is missing')
        connection = connect()
        connection.begin()
        try:
            with connection.cursor() as cursor:
                # Storefront-owned stock is rechecked under locks to prevent overselling.
                locked_quote = price_order(order['items'], load_inventory(cursor, item_ids, lock=True))
                error_response = check_quote(order, locked_quote)
                if error_response:
                    connection.rollback()
                    return error_response
                if money(locked_quote['total']) != money(quote['total']):
                    connection.rollback()
                    return respond(409, {'error': 'Prices have changed. Review the updated total before confirming.',
                                         'priceChanged': True, 'unavailable': []})
                quote = locked_quote
                confirmation = f'CS-{uuid.uuid4().hex[:16].upper()}'
                shipment = shipping_request(order, quote, confirmation)
                payment_token = process_payment(order['payment'], quote['total'], confirmation)
                save_order(cursor, order, quote, confirmation, payment_token)
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
    except PaymentRejected:
        return respond(402, {'error': 'payment was rejected; check the payment information'})
    except (KeyError, ValueError, InvalidOperation, OverflowError, TypeError,
            OSError, ServiceError, *DB_ERRORS) as error:
        # Never log exception messages: database/HTTP errors may contain payment data.
        print(json.dumps({'event': 'order_failed', 'errorType': type(error).__name__,
                          'confirmationNumber': confirmation, 'paymentToken': payment_token}))
        return respond(502, {'error': 'Order could not be completed. If payment was attempted, check with the store before retrying.'})
    shipping_status = 'accepted'
    try:
        publish_shipping(shipment)
    except Exception as error:
        # The order is already committed. Do not return a checkout failure and cause repayment.
        shipping_status = 'pending_manual_replay'
        print(json.dumps({'event': 'shipping_publish_failed', 'confirmationNumber': confirmation,
                          'errorType': type(error).__name__}))
    return respond(200, {**quote, 'confirmationNumber': confirmation, 'shippingStatus': shipping_status})

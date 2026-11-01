"""Order processing and non-mutating price previews through one POST endpoint.

Stock and prices are read from the ITEM table in MySQL (backend/db/schema.sql). A confirmed order is
saved to SHIPPING_INFO, PAYMENT_INFO, CUSTOMER_ORDER and CUSTOMER_ORDER_LINE_ITEM, and its quantities
are taken out of ITEM.AVAILABLE_QUANTITY, all in one transaction.
Connection settings come from the DB_HOST, DB_USER, DB_PASSWORD and DB_NAME environment variables.
"""
import json
import os
import uuid
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

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
                                      ssl_verify_cert=True, ssl_verify_identity=True)
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


def save_order(cursor, order, quote, confirmation):
    shipping, payment = order['shipping'], order['payment']
    cursor.execute(
        'INSERT INTO SHIPPING_INFO (NAME, ADDRESS1, ADDRESS2, CITY, STATE, COUNTRY, POSTAL_CODE, EMAIL) '
        'VALUES (%s, %s, %s, %s, %s, %s, %s, %s)',
        (text(shipping, 'fullName'), text(shipping, 'address'), text(shipping, 'apartment'), text(shipping, 'city'),
         text(shipping, 'state'), text(shipping, 'country'), text(shipping, 'zip'), text(shipping, 'email')))
    shipping_id = cursor.lastrowid
    cursor.execute(
        'INSERT INTO PAYMENT_INFO (HOLDER_NAME, CARD_NUM, EXP_DATE, CVV) VALUES (%s, %s, %s, %s)',
        (text(payment, 'cardholderName'), text(payment, 'cardNumber'), text(payment, 'expirationDate'),
         text(payment, 'cvv')))
    payment_id = cursor.lastrowid
    cursor.execute(
        'INSERT INTO CUSTOMER_ORDER (CONFIRMATION_NUMBER, CUSTOMER_NAME, CUSTOMER_EMAIL, SHIPPING_INFO_ID_FK, '
        'PAYMENT_INFO_ID_FK, TOTAL) VALUES (%s, %s, %s, %s, %s, %s)',
        (confirmation, text(shipping, 'fullName'), text(shipping, 'email'), shipping_id, payment_id, quote['total']))
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
    item_ids = {item['id'] for item in order['items']}
    try:
        connection = connect()
        # A preview never creates a confirmation, even for an empty or unavailable bag.
        if order.get('preview', False):
            with connection.cursor() as cursor:
                return respond(200, price_order(order['items'], load_inventory(cursor, item_ids)))
        connection.begin()
        try:
            with connection.cursor() as cursor:
                quote = price_order(order['items'], load_inventory(cursor, item_ids, lock=True))
                if quote['unavailable']:
                    connection.rollback()
                    return respond(409, {'error': 'one or more items are unavailable', 'unavailable': quote['unavailable']})
                if 'expectedTotal' in order and money(order['expectedTotal']) != money(quote['total']):
                    connection.rollback()
                    return respond(409, {'error': 'Prices have changed. Review the updated total before confirming.', 'priceChanged': True, 'unavailable': []})
                confirmation = f'CS-{uuid.uuid4().hex[:8].upper()}'
                save_order(cursor, order, quote, confirmation)
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
    except (KeyError, ValueError, InvalidOperation, OverflowError, *DB_ERRORS) as error:
        # The cause goes to CloudWatch only; a KeyError names the missing environment variable.
        print(f'order database error: {error!r}')
        return respond(502, {'error': 'inventory database is unavailable or returned invalid data'})
    return respond(200, {**quote, 'confirmationNumber': confirmation})

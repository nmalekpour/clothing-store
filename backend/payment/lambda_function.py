"""Independent simulated payment service. Test cards only; CVV is never stored."""
import json
import os
import uuid
from decimal import Decimal, InvalidOperation

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
                    'password': os.environ['DB_PASSWORD'], 'database': os.environ.get('DB_NAME', 'paymentdb'),
                    'port': int(os.environ.get('DB_PORT', '3306'))}
        # TLS verified against the bundled RDS CA (backend/db/rds-ca.pem), which also lets pymysql use
        # MySQL 8's caching_sha2_password login without extra crypto libraries.
        _connection = pymysql.connect(**settings, connect_timeout=5, autocommit=True, ssl_ca=CA_BUNDLE,
                                      ssl_verify_cert=True, ssl_verify_identity=True, read_timeout=5, write_timeout=5)
    return _connection



def validate_payment(body):
    if not isinstance(body, dict) or not isinstance(body.get('payment'), dict):
        raise ValueError('payment must be an object')
    raw_amount = body.get('amount')
    if isinstance(raw_amount, bool) or not isinstance(raw_amount, (int, float)):
        raise ValueError('amount must be a non-negative number')
    amount = Decimal(str(raw_amount))
    if not amount.is_finite() or amount < 0 or amount > Decimal('9999999999.99') or amount != amount.quantize(Decimal('0.01')):
        raise ValueError('amount must be a non-negative amount with at most two decimal places')
    payment = body['payment']
    holder = required_text(payment, 'cardholderName')
    card = required_text(payment, 'cardNumber', 32).replace(' ', '').replace('-', '')
    if not card.isascii() or not card.isdigit() or not 12 <= len(card) <= 19:
        raise ValueError('cardNumber must contain 12 to 19 digits')
    expiration = required_text(payment, 'expirationDate', 5)
    import re
    if not re.fullmatch(r'(0[1-9]|1[0-2])/[0-9]{2}', expiration):
        raise ValueError('expirationDate must use MM/YY')
    cvv = required_text(payment, 'cvv', 4)
    if not cvv.isascii() or not cvv.isdigit() or len(cvv) not in (3, 4):
        raise ValueError('cvv must contain 3 or 4 digits')
    reference = body.get('orderReference')
    if reference is not None:
        reference = required_text(body, 'orderReference', 64)
    return holder, card, expiration, str(amount), reference


def lambda_handler(event, context):
    event = event or {}
    method = event.get('httpMethod') or (event.get('requestContext') or {}).get('http', {}).get('method')
    if method == 'OPTIONS':
        return respond(204, {})
    if method and method != 'POST':
        return respond(405, {'error': 'method not allowed'})
    try:
        body = json.loads(event.get('body') or '')
        values = validate_payment(body)
    except (ValueError, TypeError, InvalidOperation) as error:
        # Validation messages contain field names only, never submitted values.
        return respond(400, {'error': str(error) if not isinstance(error, json.JSONDecodeError) else 'invalid JSON'})
    try:
        token = f'PAY-{uuid.uuid4().hex}'
        with connect().cursor() as cursor:
            cursor.execute('INSERT INTO PAYMENT (PAYMENT_TOKEN, HOLDER_NAME, CARD_NUM, EXP_DATE, AMOUNT, ORDER_REFERENCE) '
                           'VALUES (%s, %s, %s, %s, %s, %s)', (token, *values))
        return respond(200, {'paymentToken': token})
    except (KeyError, OSError, *DB_ERRORS) as error:
        print(json.dumps({'event': 'payment_failed', 'errorType': type(error).__name__}))
        return respond(502, {'error': 'payment database is unavailable'})

"""Temporary Console-only database initializer; do NOT attach an API/trigger.

SETUP_TARGET=payment|shipping|order, DB_HOST/USER/PASSWORD, optional DB_PORT.
For payment/shipping also set APP_DB_USER and APP_DB_PASSWORD to create the service account.
Only fixed bundled SQL is executed; request event data is ignored.
"""
import os
import re
from pathlib import Path
import pymysql

ROOT = Path(__file__).resolve().parent
TARGETS = {'payment': ('paymentdb', 'payment.sql', 'PAYMENT'),
           'shipping': ('shippingdb', 'shipping.sql', 'SHIPMENT'),
           'order': ('clothingstore', 'lab-integration-migration.sql', None)}


def lambda_handler(event, context):
    target = os.environ['SETUP_TARGET']
    database, filename, table = TARGETS[target]
    app_user = os.environ.get('APP_DB_USER', '')
    if table and (not re.fullmatch(r'[A-Za-z0-9_]{1,32}', app_user) or not os.environ.get('APP_DB_PASSWORD')):
        raise ValueError('Set APP_DB_USER and APP_DB_PASSWORD for the independent service account')
    with pymysql.connect(host=os.environ['DB_HOST'], user=os.environ['DB_USER'],
                         password=os.environ['DB_PASSWORD'], port=int(os.environ.get('DB_PORT', '3306')),
                         connect_timeout=5, read_timeout=5, write_timeout=5, autocommit=True,
                         ssl_ca=str(ROOT / 'rds-ca.pem'), ssl_verify_cert=True, ssl_verify_identity=True) as connection:
        with connection.cursor() as cursor:
            if target == 'order':
                cursor.execute("SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = %s "
                               "AND TABLE_NAME = 'CUSTOMER_ORDER' AND COLUMN_NAME = 'PAYMENT_TOKEN'", (database,))
                if not cursor.fetchone()[0]:
                    cursor.execute('ALTER TABLE clothingstore.CUSTOMER_ORDER ADD COLUMN PAYMENT_TOKEN varchar(64) NULL')
            else:
                sql = (ROOT / filename).read_text()
                sql = re.sub(r'^\s*--.*$', '', sql, flags=re.M)
                for statement in sql.split(';'):
                    if statement.strip():
                        cursor.execute(statement)
                cursor.execute("CREATE USER IF NOT EXISTS %s@'%%' IDENTIFIED BY %s REQUIRE SSL",
                               (app_user, os.environ['APP_DB_PASSWORD']))
                cursor.execute(f"GRANT SELECT, INSERT ON {database}.{table} TO %s@'%%'", (app_user,))
    return {'initialized': target, 'database': database}

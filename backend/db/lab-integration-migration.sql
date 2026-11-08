-- Run ONCE on existing storefront MySQL, before uploading the new order Lambda.
-- No DROP, DELETE or UPDATE; historical orders/payment records remain untouched.
USE clothingstore;
ALTER TABLE CUSTOMER_ORDER ADD COLUMN PAYMENT_TOKEN varchar(64) NULL;
-- PAYMENT_INFO_ID_FK is already nullable in schema.sql. New orders leave it NULL.
-- To check whether the migration has already run:
-- SHOW COLUMNS FROM CUSTOMER_ORDER LIKE 'PAYMENT_TOKEN';

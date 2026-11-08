-- Run ONLY on the independent payment RDS instance. No storefront grants.
CREATE DATABASE IF NOT EXISTS paymentdb;
USE paymentdb;
CREATE TABLE IF NOT EXISTS PAYMENT (
  ID bigint auto_increment primary key,
  PAYMENT_TOKEN varchar(64) not null unique,
  HOLDER_NAME varchar(255) not null,
  CARD_NUM varchar(19) not null,
  EXP_DATE varchar(5) not null,
  AMOUNT decimal(12,2) not null,
  ORDER_REFERENCE varchar(64),
  CREATED_AT timestamp not null default CURRENT_TIMESTAMP
);
-- Synthetic lab cards only. CVV intentionally has no column.

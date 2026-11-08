-- Run ONLY on the independent shipping RDS instance. No storefront grants.
CREATE DATABASE IF NOT EXISTS shippingdb;
USE shippingdb;
CREATE TABLE IF NOT EXISTS SHIPMENT (
  ID bigint auto_increment primary key,
  SHIPPING_TOKEN varchar(64) not null unique,
  SHIPMENT_REQUEST_ID varchar(64) not null unique,
  BUSINESS_ID varchar(64) not null,
  ADDRESS_JSON JSON not null,
  PACKET_COUNT int not null,
  WEIGHTS_JSON JSON not null,
  CREATED_AT timestamp not null default CURRENT_TIMESTAMP
);

-- Lab 8 data tier (MySQL on AWS RDS).
-- ITEM.ITEM_NUMBER is the product id the API and the frontend cart use;
-- ITEM.ID is the database's own auto-increment key.

CREATE DATABASE IF NOT EXISTS clothingstore;
USE clothingstore;

DROP TABLE IF EXISTS CUSTOMER_ORDER_LINE_ITEM;
DROP TABLE IF EXISTS CUSTOMER_ORDER;
DROP TABLE IF EXISTS PAYMENT_INFO;
DROP TABLE IF EXISTS SHIPPING_INFO;
DROP TABLE IF EXISTS ITEM;

CREATE TABLE ITEM (
  ID int auto_increment primary key,
  ITEM_NUMBER int not null unique,
  NAME varchar(255),
  DESCRIPTION varchar(255),
  AVAILABLE_QUANTITY int,
  UNIT_PRICE double,
  IMAGE varchar(255)
);

CREATE TABLE PAYMENT_INFO (
  ID int auto_increment primary key,
  HOLDER_NAME varchar(255),
  CARD_NUM varchar(255),
  EXP_DATE varchar(255),
  CVV varchar(4)
);

CREATE TABLE SHIPPING_INFO (
  ID int auto_increment primary key,
  NAME varchar(255),
  ADDRESS1 varchar(255),
  ADDRESS2 varchar(255),
  CITY varchar(255),
  STATE varchar(255),
  COUNTRY varchar(255),
  POSTAL_CODE varchar(255),
  EMAIL varchar(255)
);

CREATE TABLE CUSTOMER_ORDER (
  ID int auto_increment primary key,
  CONFIRMATION_NUMBER varchar(32),
  CUSTOMER_NAME varchar(255),
  CUSTOMER_EMAIL varchar(255),
  SHIPPING_INFO_ID_FK int,
  PAYMENT_INFO_ID_FK int,
  PAYMENT_TOKEN varchar(64),
  TOTAL double,
  STATUS varchar(255) default 'New',
  FOREIGN KEY (SHIPPING_INFO_ID_FK) REFERENCES SHIPPING_INFO(ID),
  FOREIGN KEY (PAYMENT_INFO_ID_FK) REFERENCES PAYMENT_INFO(ID)
);

CREATE TABLE CUSTOMER_ORDER_LINE_ITEM (
  ID int auto_increment primary key,
  ITEM_ID int,
  ITEM_NAME varchar(255),
  QUANTITY int,
  UNIT_PRICE double,
  CUSTOMER_ORDER_ID_FK int,
  FOREIGN KEY (CUSTOMER_ORDER_ID_FK) REFERENCES CUSTOMER_ORDER(ID)
);

INSERT INTO ITEM (ITEM_NUMBER, NAME, DESCRIPTION, AVAILABLE_QUANTITY, UNIT_PRICE, IMAGE) VALUES
  (0, 'Sage Dress', 'Flowing midi dress in soft sage linen.', 12, 280.00, '/images/sage-dress.jpeg'),
  (1, 'White Tank', 'Ribbed cotton tank, an everyday essential.', 40, 90.00, '/images/white-tank.jpeg'),
  (2, 'Peacoat', 'Double-breasted wool peacoat.', 5, 550.00, '/images/coat.jpeg'),
  (3, 'Wide-Leg Pants', 'High-waisted trousers with a relaxed wide leg.', 20, 148.00, '/images/pants.png'),
  (4, 'Diamond Lariat Necklace', 'Delicate lariat chain with a diamond drop.', 2, 1200.00, '/images/necklace.png');

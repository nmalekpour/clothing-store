# Clothing Store — CSE 5234 Group Project

React + Vite storefront connected to the Lab 7 inventory and order APIs.

## Getting started

```bash
npm install
cp .env.example .env  # First-time setup only.
npm run dev     # http://localhost:5173
```

## Routes

| Path | Component |
| --- | --- |
| `/` | `src/components/Home.jsx` — landing page and featured collection |
| `/about` | `src/components/About.jsx` — mission, vision, strategy, and three team profiles |
| `/contact` | `src/components/Contact.jsx` — demo inquiry form, returns, and FAQ |
| `/purchase` | `src/components/Purchase.jsx` — API catalog, add to cart |
| `/purchase/paymentEntry` | `src/components/PaymentEntry.jsx` — card number, expiration, CVV, holder name |
| `/purchase/shippingEntry` | `src/components/ShippingEntry.jsx` — name, address lines, city, state, zip |
| `/purchase/viewOrder` | `src/components/ViewOrder.jsx` — order summary + confirm |
| `/purchase/viewConfirmation` | `src/components/Confirmation.jsx` — greeting, confirmation number, summary |

Product images go in `public/images/`.

All pages share the navigation and footer in `src/components/SiteLayout.jsx`.
The contact form uses browser validation and does not send or save messages.
Review the contact details and service policies before submission.


## Lab 7 API integration

`.env` sets `VITE_API_BASE_URL` to the shared AWS API Gateway stage:
`https://xnigucru41.execute-api.us-east-2.amazonaws.com/dev`.
Restart Vite after changing it; production builds read this value at build time.

- `src/api.js` uses axios for `GET /inventory-management/inventory` and
  `POST /order-processing/order`, with a 15-second timeout.
- Home (including the hero image), About product image, catalog, prices, descriptions, images, stock,
  and order review use inventory responses. There is no fallback product list.
- The cart stores quantities by product ID and accepts the old array format.
  Missing products or reduced stock block checkout until the bag is adjusted.
- Checkout sends `{ items: [{ id, quantity }], payment, shipping, expectedTotal }` with numeric IDs.
  Payment and shipping come from the forms. Submission disables the confirmation
  button while pending.
- Only a successful response with `confirmationNumber` opens the confirmation page
  and clears the cart and saved payment. Confirmation data in session storage
  includes only the last four card digits, not the full card number or CVV.
- HTTP 400 displays the service error. HTTP 409 lists requested and available
  quantities and reloads inventory. Errors preserve the bag and form data.
  Inventory failures show a Retry button.
- Payment and shipping Continue actions enforce required form fields; saving an
  address keeps it selected for checkout.

## Validation

```bash
npm run build
npm run lint
npm test
```

Contract tests cover API data validation, numeric order IDs and quantities,
backend confirmation numbers, previews, and migration of saved carts.

For a manual browser check, add a product, fill payment and shipping, review,
and confirm using lab test data. Verify the Network panel shows a POST and the
confirmation page displays its returned number. To exercise errors deterministically,
intercept the APIs in browser automation: inventory 503 should show Retry; order
400/409 should show the response error and preserve the cart. A 409 should also
show each item's requested and available quantity.


## Backend pricing and inventory validation update

Deploy the updated Order Lambda **before** using this frontend version for checkout.
Older deployments return only a confirmation number and do not implement price previews.
The frontend blocks checkout if it cannot retrieve a valid server quote; it does not
invent a total or fall back to hardcoded prices.

The same existing `POST /order-processing/order` supports:

- **Preview:** `{ "preview": true, "items": [{ "id": 0, "quantity": 2 }] }`.
  Payment/shipping are omitted. Returns `{ items, total, itemCount, unavailable }`
  without creating a confirmation. Empty bags are supported. Each item includes
  authoritative inventory fields, quantity, and subtotal.
- **Confirm:** `{ "items": [...], "payment": {...}, "shipping": {...}, "expectedTotal": 560 }`.
  The backend fetches inventory again, merges duplicate IDs, checks combined stock,
  and calculates prices using decimal arithmetic. Returns a confirmation plus the
  authoritative items and total. Client-supplied prices/subtotals are ignored.
- A changed total returns HTTP 409 and requires a new review. Insufficient combined
  quantity returns HTTP 409 with `{ id, requestedQty, availableQty }` per shortage.

The cart and review display backend subtotals/totals. Quantity controls and form
validation provide UI feedback; the backend makes the final stock and price decisions.
Brand copy, team biographies, labels, and layout remain presentation content.

### Deploy to the shared AWS account

Configure your assigned IAM credentials locally using `aws configure --profile lab7`
(or use your organization's SSO/temporary-credential setup). Never commit credentials.
Then run:

```bash
# Read-only: verify that the profile can access the existing API and Lambda.
python3 scripts/deploy_lambda.py --service order --profile lab7
# Run backend regression tests, back up the existing code, and update its Lambda.
python3 scripts/deploy_lambda.py --service order --profile lab7 --deploy
```

Use `--service inventory` for the inventory Lambda. The script discovers the existing
integration (`POST /order-processing/order` or `GET /inventory-management/inventory`) in API `xnigucru41` in `us-east-2`,
checks the runtime and handler, uses the Lambda revision to avoid overwriting concurrent
changes, and verifies the uploaded checksum. It changes no API Gateway routes or IAM.
Lambda aliases/versions require their existing release process; the script stops if
one is detected. Since routes/integrations remain unchanged, this Lambda code update
does not require an API Gateway stage deployment.

For manual console upload, build the ZIPs (runs the tests, makes no AWS calls):

```bash
python3 scripts/deploy_lambda.py --service order --package       # artifacts/order-processing.zip
python3 scripts/deploy_lambda.py --service inventory --package   # artifacts/inventory.zip
```

Each ZIP contains `lambda_function.py`, `pymysql`, and the RDS CA bundle; upload it only to the
matching existing Lambda with handler `lambda_function.lambda_handler`.

After deployment, verify duplicate IDs with quantities 7 and 7 against stock 12 return
409 with `requestedQty: 14`; preview returns totals with no confirmation; normal checkout
returns a confirmation and matching server total. Then complete the browser flow again.

## Lab 8 data tier (AWS RDS MySQL)

Inventory and orders live in the RDS MySQL instance `database-1` (us-east-2), database `clothingstore`.

- `backend/db/schema.sql` creates `ITEM`, `CUSTOMER_ORDER`, `CUSTOMER_ORDER_LINE_ITEM`,
  `PAYMENT_INFO`, and `SHIPPING_INFO` and seeds the five products. **It drops those tables first.**
  `ITEM.ITEM_NUMBER` is the product `id` the API and cart use; `ITEM.IMAGE` holds the frontend image path.
- `backend/db/test_order.sql` inserts one order by hand and reads it back with a join.
- The inventory Lambda reads `ITEM`. The order Lambda reads stock and prices from `ITEM`, then in one
  transaction (with the requested `ITEM` rows locked) saves shipping, payment, the order and its line
  items, and subtracts the ordered quantities from `ITEM.AVAILABLE_QUANTITY`. Previews read only.
- Both Lambdas connect with TLS verified against `backend/db/rds-ca.pem` (Amazon's public RDS CA bundle)
  and read `DB_HOST`, `DB_USER`, `DB_PASSWORD`, and optionally `DB_NAME` (default `clothingstore`)
  from their environment variables. Never commit the password.
- The Lambdas run in the database's VPC with no internet access, so the order Lambda reads `ITEM`
  directly instead of calling the inventory API.

`PAYMENT_INFO` stores the card number and CVV because the lab schema requires it. Use test cards only;
a real store must never keep CVVs and would store a payment-processor token instead of the card number.

### One-time AWS setup

1. Connect as the master user (password in Secrets Manager) and run both SQL files:
   `mysql -h <endpoint> -u admin -p < backend/db/schema.sql`.
2. Create an app user for the Lambdas. The master password rotates in Secrets Manager, and a
   VPC Lambda cannot reach Secrets Manager without a paid endpoint:
   ```sql
   CREATE USER 'store_app'@'%' IDENTIFIED BY '<choose a password>' REQUIRE SSL;
   GRANT SELECT ON clothingstore.ITEM TO 'store_app'@'%';
   GRANT UPDATE (AVAILABLE_QUANTITY) ON clothingstore.ITEM TO 'store_app'@'%';
   GRANT INSERT ON clothingstore.CUSTOMER_ORDER TO 'store_app'@'%';
   GRANT INSERT ON clothingstore.CUSTOMER_ORDER_LINE_ITEM TO 'store_app'@'%';
   GRANT INSERT ON clothingstore.PAYMENT_INFO TO 'store_app'@'%';
   GRANT INSERT ON clothingstore.SHIPPING_INFO TO 'store_app'@'%';
   ```
3. For **each** Lambda: Configuration → VPC → the database's VPC, its subnets, and security group
   `ec2-rds-1` (the database's `rds-ec2-1` group already allows MySQL from it; check its inbound rule).
   The execution role needs `AWSLambdaVPCAccessExecutionRole`. Set the environment variables above
   (`DB_USER=store_app`) and raise the timeout to 15 seconds.
4. Upload the ZIPs (or use `--deploy`), then run `python3 scripts/verify_api.py`.

Additional backend checks:

```bash
python3 -B backend/inventory/test_lambda.py
python3 -B backend/order-processing/test_lambda.py
```

After deploying, run all live API checks (including synthetic lab orders). Since Lab 8,
each run saves one test order to the database and takes 1 unit of that item's stock:

```bash
python3 scripts/verify_api.py
```

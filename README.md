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
python3 scripts/deploy_order.py --profile lab7
# Run backend regression tests, back up the existing code, and update its Lambda.
python3 scripts/deploy_order.py --profile lab7 --deploy
```

The script discovers the existing POST integration in API `xnigucru41` in `us-east-2`,
checks the runtime and handler, uses the Lambda revision to avoid overwriting concurrent
changes, and verifies the uploaded checksum. It changes no API Gateway routes or IAM.
Lambda aliases/versions require their existing release process; the script stops if
one is detected. Since routes/integrations remain unchanged, this Lambda code update
does not require an API Gateway stage deployment.

For manual console upload, `artifacts/order-processing.zip` contains `lambda_function.py`;
use it only for the existing Order Lambda with handler `lambda_function.lambda_handler`.
The ZIP can be regenerated with:

```bash
python3 -m zipfile -c artifacts/order-processing.zip backend/order-processing/lambda_function.py
```

After deployment, verify duplicate IDs with quantities 7 and 7 against stock 12 return
409 with `requestedQty: 14`; preview returns totals with no confirmation; normal checkout
returns a confirmation and matching server total. Then complete the browser flow again.

Additional backend checks:

```bash
python3 -B backend/inventory/test_lambda.py
python3 -B backend/order-processing/test_lambda.py
```

After deploying, run all live API checks (including synthetic lab orders):

```bash
python3 scripts/verify_api.py
```

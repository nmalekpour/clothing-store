# Clothing Store — CSE 5234 Group Project

React + Vite storefront (presentation tier, Lab 5).

## Getting started

```bash
npm install
npm run dev     # http://localhost:5173
```

## Routes

| Path | Component |
| --- | --- |
| `/purchase` | `src/components/Purchase.jsx` — catalog of 5 items, add to cart |
| `/purchase/paymentEntry` | `src/components/PaymentEntry.jsx` — card number, expiration, CVV, holder name |
| `/purchase/shippingEntry` | `src/components/ShippingEntry.jsx` — name, address lines, city, state, zip |
| `/purchase/viewOrder` | `src/components/ViewOrder.jsx` — order summary + confirm |
| `/purchase/viewConfirmation` | `src/components/Confirmation.jsx` — greeting, confirmation number, summary |

Product images go in `public/images/`.

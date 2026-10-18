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
| `/` | `src/components/Home.jsx` — landing page and featured collection |
| `/about` | `src/components/About.jsx` — mission, vision, strategy, and three team profiles |
| `/contact` | `src/components/Contact.jsx` — demo inquiry form, returns, and FAQ |
| `/purchase` | `src/components/Purchase.jsx` — catalog of 5 items, add to cart |
| `/purchase/paymentEntry` | `src/components/PaymentEntry.jsx` — card number, expiration, CVV, holder name |
| `/purchase/shippingEntry` | `src/components/ShippingEntry.jsx` — name, address lines, city, state, zip |
| `/purchase/viewOrder` | `src/components/ViewOrder.jsx` — order summary + confirm |
| `/purchase/viewConfirmation` | `src/components/Confirmation.jsx` — greeting, confirmation number, summary |

Product images go in `public/images/`.

All pages share the navigation and footer in `src/components/SiteLayout.jsx`.
The contact form uses browser validation and does not send or save messages.
Before submission, replace the three team profile placeholders in `About.jsx`
with real names, photos, education, experience, and interests. Replace the sample
contact details and review the proposed service policies in `Contact.jsx`.

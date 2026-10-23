import { useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { loadCart, readSavedValue } from '../cart'
import { errorMessage, submitOrder } from '../api'
import useQuote from '../useQuote'
import QuoteStatus from './QuoteStatus'

const formatPrice = (amount) =>
  amount.toLocaleString('en-US', { style: 'currency', currency: 'USD' })

const hasText = (value) => typeof value === 'string' && value.trim().length > 0

function ViewOrder() {
  const navigate = useNavigate()
  const [submitting, setSubmitting] = useState(false)
  const submittingRef = useRef(false)
  const [submitError, setSubmitError] = useState('')
  const [unavailable, setUnavailable] = useState([])
  const [confirmed, setConfirmed] = useState(false)
  const [checkout] = useState(() => ({
    cart: loadCart(),
    payment: readSavedValue('paymentInfo', {}),
    shipping: readSavedValue('selectedShippingAddress', {}),
  }))
  const { cart, payment, shipping } = checkout
  const pricing = useQuote(cart)
  const { quote, loading, error, reload } = pricing
  const items = quote?.items ?? []
  const itemCount = quote?.itemCount
  const cardDigits = typeof payment.cardNumber === 'string'
    ? payment.cardNumber.replace(/\D/g, '')
    : ''
  const paymentReady = ['cardholderName', 'cardNumber', 'expirationDate', 'cvv', 'billingZip'].every(
    (field) => hasText(payment[field]),
  ) && cardDigits.length > 0
  const hasPaymentDetails = hasText(payment.cardholderName)
    || cardDigits.length > 0
    || hasText(payment.expirationDate)
    || hasText(payment.billingZip)
  const shippingReady = ['fullName', 'address', 'city', 'state', 'zip'].every(
    (field) => hasText(shipping[field]),
  )
  const canConfirm = !!quote && !quote.unavailable.length
    && items.length > 0 && paymentReady && shippingReady

  const handleConfirm = async (event) => {
    event.preventDefault()
    if (!confirmed || !canConfirm || submittingRef.current) return
    submittingRef.current = true
    setSubmitting(true)
    setSubmitError('')
    setUnavailable([])

    try {
      const result = await submitOrder({ items, payment, shipping, expectedTotal: quote.total })

      // Pass only the card's last four digits to the confirmation page.
      const order = {
        confirmationNumber: result.confirmationNumber,
        items: result.items,
        total: result.total,
        shipping,
        payment: {
          cardholderName: payment.cardholderName,
          lastFour: cardDigits.slice(-4),
          expirationDate: payment.expirationDate,
        },
      }
      try {
        sessionStorage.setItem('confirmedOrder', JSON.stringify(order))
      } catch {
        // Navigation state still works when browser storage is unavailable.
      }
      try {
        localStorage.removeItem('cart')
        localStorage.removeItem('paymentInfo')
      } catch {
        // The accepted order can still be displayed through navigation state.
      }
      navigate('/purchase/viewConfirmation', { state: { order }, replace: true })
    } catch (cause) {
      setSubmitError(errorMessage(cause, 'Unable to confirm your order. Check your order before trying again.'))
      if (cause.response?.status === 409) {
        setUnavailable(Array.isArray(cause.response.data.unavailable) ? cause.response.data.unavailable : [])
        setConfirmed(false)
        reload()
      }
    } finally {
      submittingRef.current = false
      setSubmitting(false)
    }
  }

  return (
    <div className="view-order">
      <h1 className="order-title">Review Your Order</h1>

      <QuoteStatus {...pricing} />
      {quote?.unavailable.map(item => (
        <p className="order-notice" role="alert" key={item.id}>
          {items.find(product => product.id === item.id)?.name || `Item ${item.id}`}: requested {item.requestedQty}, available {item.availableQty}. Edit your bag to continue.
        </p>
      ))}
      <section aria-labelledby="order-items-heading">
        <div className="order-section-heading">
          <h2 id="order-items-heading">Your Bag ({itemCount ?? '…'})</h2>
          <Link to="/purchase">Edit bag</Link>
        </div>
        {!loading && !error && items.length === 0 ? (
          <p className="order-notice" role="status">Your bag is empty. Add items before confirming your order.</p>
        ) : (
          <ul className="order-items">
            {items.map((item) => (
              <li className="order-item" key={item.id}>
                <img src={item.image} alt={item.name} />
                <div className="order-item-details">
                  <h3>{item.name}</h3>
                  <p>{formatPrice(item.price)} each</p>
                  <p>Quantity: {item.quantity}</p>
                </div>
                <strong className="order-item-subtotal">{formatPrice(item.subtotal)}</strong>
              </li>
            ))}
          </ul>
        )}
        <div className="order-total">
          <span>Order Total</span>
          <strong>{quote ? formatPrice(quote.total) : '—'}</strong>
        </div>
      </section>

      <div className="order-details">
        <section aria-labelledby="order-shipping-heading">
          <div className="order-section-heading">
            <h2 id="order-shipping-heading">Ship To</h2>
            <Link to="/purchase/shippingEntry">Edit shipping</Link>
          </div>
          {shippingReady ? (
            <address>
              {shipping.fullName}<br />
              {shipping.address}<br />
              {hasText(shipping.apartment) && <>{shipping.apartment}<br /></>}
              {shipping.city}, {shipping.state} {shipping.zip}
            </address>
          ) : (
            <p className="order-notice" role="status">Complete your shipping address before confirming.</p>
          )}
        </section>

        <section aria-labelledby="order-payment-heading">
          <div className="order-section-heading">
            <h2 id="order-payment-heading">Payment</h2>
            <Link to="/purchase/paymentEntry">Edit payment</Link>
          </div>
          {hasPaymentDetails && (
            <div>
              {hasText(payment.cardholderName) && <p>{payment.cardholderName}</p>}
              {cardDigits.length > 0 && <p>Card ending in {cardDigits.slice(-4)}</p>}
              {hasText(payment.expirationDate) && <p>Expires {payment.expirationDate}</p>}
              {hasText(payment.billingZip) && <p>Billing ZIP: {payment.billingZip}</p>}
            </div>
          )}
          {!paymentReady && (
            <p className="order-notice" role="status">Complete your payment information before confirming.</p>
          )}
        </section>
      </div>

      {submitError && <div className="order-notice" role="alert"><p>{submitError}</p><ul>{unavailable.map((item, index) => <li key={index}>{items.find(product => product.id === item.id)?.name || `Item ${item.id}`}: requested {item.requestedQty}, available {item.availableQty}.</li>)}</ul></div>}
      <form aria-busy={submitting} className="order-confirmation" onSubmit={handleConfirm}>
        <label className="order-confirm-check">
          <input
            type="checkbox"
            checked={confirmed}
            onChange={(event) => setConfirmed(event.target.checked)}
            disabled={!canConfirm || submitting}
            required
          />
          <span>I have reviewed my order and confirm that the details are correct.</span>
        </label>
        <div className="order-actions">
          <Link to="/purchase/shippingEntry">Back to shipping</Link>
          <button className="btn btn-primary" type="submit" disabled={!canConfirm || !confirmed || submitting}>
            {submitting ? 'Placing order…' : 'Confirm Order'}
          </button>
        </div>
      </form>
    </div>
  )
}

export default ViewOrder

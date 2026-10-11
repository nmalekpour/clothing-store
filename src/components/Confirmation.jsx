import { Link, useLocation } from 'react-router-dom'

function isConfirmedOrder(order) {
  return typeof order?.confirmationNumber === 'string'
    && Number.isFinite(order.total)
    && Array.isArray(order.items)
    && order.items.length > 0
    && order.items.every((item) => typeof item?.name === 'string'
      && Number.isSafeInteger(item.quantity) && item.quantity > 0
      && Number.isFinite(item.price) && Number.isFinite(item.subtotal))
    && ['fullName', 'address', 'city', 'state', 'zip'].every(
      (field) => typeof order.shipping?.[field] === 'string',
    )
    && typeof order.payment?.cardholderName === 'string'
    && typeof order.payment?.lastFour === 'string'
    && typeof order.payment?.expirationDate === 'string'
}

function readConfirmedOrder() {
  try {
    const order = JSON.parse(sessionStorage.getItem('confirmedOrder'))
    return isConfirmedOrder(order) ? order : null
  } catch {
    return null
  }
}

const formatPrice = (amount) =>
  amount.toLocaleString('en-US', { style: 'currency', currency: 'USD' })

function Confirmation() {
  const location = useLocation()
  const order = isConfirmedOrder(location.state?.order)
    ? location.state.order
    : readConfirmedOrder()

  if (!order) {
    return (
      <div className="view-order confirmation-page">
        <h1 className="order-title">No confirmed order yet</h1>
        <p>Your order will appear here after you confirm it.</p>
        <div className="order-actions">
          <Link to="/purchase/viewOrder">Review your order</Link>
          <Link to="/purchase">Continue shopping</Link>
        </div>
      </div>
    )
  }

  const { items, total, shipping, payment, confirmationNumber } = order
  const itemCount = items.reduce((sum, item) => sum + item.quantity, 0)

  return (
    <div className="view-order confirmation-page">
      <header className="confirmation-header">
        <p className="confirmation-status">Order Confirmed</p>
        <h1 className="order-title">Thank you for your order!</h1>
        <p>Thank you, {shipping.fullName}.</p>
        <p className="confirmation-number">Confirmation number: <strong>{confirmationNumber}</strong></p>
      </header>

      <section aria-labelledby="confirmation-items-heading">
        <div className="order-section-heading">
          <h2 id="confirmation-items-heading">Order Summary ({itemCount})</h2>
        </div>
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
        <div className="order-total">
          <span>Order Total</span>
          <strong>{formatPrice(total)}</strong>
        </div>
      </section>

      <div className="order-details">
        <section aria-labelledby="confirmation-shipping-heading">
          <div className="order-section-heading">
            <h2 id="confirmation-shipping-heading">Ship To</h2>
          </div>
          <address>
            {shipping.fullName}<br />
            {shipping.address}<br />
            {shipping.apartment && <>{shipping.apartment}<br /></>}
            {shipping.city}, {shipping.state} {shipping.zip}
          </address>
        </section>
        <section aria-labelledby="confirmation-payment-heading">
          <div className="order-section-heading">
            <h2 id="confirmation-payment-heading">Payment</h2>
          </div>
          <p>{payment.cardholderName}</p>
          <p>Card ending in {payment.lastFour}</p>
          <p>Expires {payment.expirationDate}</p>
        </section>
      </div>

      <div className="order-actions confirmation-actions">
        <Link className="btn btn-primary" to="/purchase">Continue shopping</Link>
      </div>
    </div>
  )
}

export default Confirmation

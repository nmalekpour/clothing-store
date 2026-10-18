import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { PRODUCTS, emptyOrder } from '../data/products'

function loadCart() {
  const savedCart = localStorage.getItem('cart')
  return savedCart ? JSON.parse(savedCart) : PRODUCTS.map(() => 0)
}

const formatPrice = (amount) =>
  amount.toLocaleString('en-US', { style: 'currency', currency: 'USD' })

function Stepper({ value, min, onChange, label }) {
  return (
    <div className="stepper">
      <button
        type="button"
        aria-label={`Decrease ${label}`}
        onClick={() => onChange(value - 1)}
        disabled={value <= min}
      >
        −
      </button>
      <input
        type="number"
        min={min}
        aria-label={label}
        value={value}
        onChange={(event) => onChange(parseInt(event.target.value, 10) || min)}
      />
      <button type="button" aria-label={`Increase ${label}`} onClick={() => onChange(value + 1)}>
        +
      </button>
    </div>
  )
}

function Purchase() {
  const navigate = useNavigate()
  const location = useLocation()

  // Cart = order.buyQuantity, restored when coming back from a later page.
  const [cart, setCart] = useState(
    () => location.state?.order?.buyQuantity ?? loadCart(),
  )
  // Quantity picked on each catalog card before clicking "Add to cart".
  const [pending, setPending] = useState(PRODUCTS.map(() => 1))
  const [justAdded, setJustAdded] = useState(null)

  const updateCart = (nextCart) => {
    setCart(nextCart)
    localStorage.setItem('cart', JSON.stringify(nextCart))
  }

  const setQuantity = (index, quantity) => {
    const nextCart = [...cart]
    nextCart[index] = Math.max(0, quantity || 0)
    updateCart(nextCart)
  }

  const setPendingQuantity = (index, quantity) => {
    const nextPending = [...pending]
    nextPending[index] = Math.max(1, quantity)
    setPending(nextPending)
  }

  const addToCart = (index) => {
    setQuantity(index, cart[index] + pending[index])
    setPendingQuantity(index, 1)
    setJustAdded(index)
    setTimeout(() => setJustAdded((current) => (current === index ? null : current)), 1200)
  }

  const cartLines = PRODUCTS.filter((product) => cart[product.id] > 0)
  const itemCount = cart.reduce((sum, quantity) => sum + quantity, 0)
  const total = cartLines.reduce(
    (sum, product) => sum + product.price * cart[product.id],
    0,
  )

  const handleCheckout = (event) => {
    event.preventDefault()
    const order = { ...emptyOrder(), ...location.state?.order, buyQuantity: cart }
    navigate('/purchase/paymentEntry', { state: { order } })
  }

  return (
    <div className="purchase">
      <header className="shop-heading"><p className="eyebrow">FIND YOUR NEXT FAVORITE</p><h1 className="page-title">The Collection</h1><p>Five distinctive pieces. Endless ways to make them your own.</p></header>

      <div className="purchase-layout">
        <section className="catalog" aria-label="Products">
          {PRODUCTS.map((product) => (
            <article key={product.id} className="product-card">
              <div className="product-image">
                <img src={product.image} alt={product.name} />
                {cart[product.id] > 0 && (
                  <span className="in-cart-badge">{cart[product.id]} in bag</span>
                )}
              </div>
              <div className="product-info">
                <h3>{product.name}</h3>
                <p className="price">{formatPrice(product.price)}</p>
              </div>
              <div className="product-actions">
                <Stepper
                  label={`${product.name} quantity`}
                  min={1}
                  value={pending[product.id]}
                  onChange={(quantity) => setPendingQuantity(product.id, quantity)}
                />
                <button
                  type="button"
                  className="btn"
                  onClick={() => addToCart(product.id)}
                >
                  {justAdded === product.id ? 'Added ✓' : 'Add to bag'}
                </button>
              </div>
            </article>
          ))}
        </section>

        <aside className="cart">
          <form onSubmit={handleCheckout}>
            <h2>
              Your Bag <span className="cart-count">({itemCount})</span>
            </h2>

            {cartLines.length === 0 ? (
              <p className="cart-empty">Your bag is empty.</p>
            ) : (
              <ul className="cart-lines">
                {cartLines.map((product) => (
                  <li key={product.id} className="cart-line">
                    <img src={product.image} alt="" />
                    <div className="cart-line-body">
                      <div className="cart-line-top">
                        <span className="cart-line-name">{product.name}</span>
                        <span>{formatPrice(product.price * cart[product.id])}</span>
                      </div>
                      <div className="cart-line-bottom">
                        <Stepper
                          label={`${product.name} quantity in bag`}
                          min={0}
                          value={cart[product.id]}
                          onChange={(quantity) => setQuantity(product.id, quantity)}
                        />
                        <button
                          type="button"
                          className="link-button"
                          onClick={() => setQuantity(product.id, 0)}
                        >
                          Remove
                        </button>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            )}

            <div className="cart-total">
              <span>Total</span>
              <span>{formatPrice(total)}</span>
            </div>

            <button
              type="submit"
              className="btn btn-primary btn-block"
              disabled={cartLines.length === 0}
            >
              Checkout
            </button>
          </form>
        </aside>
      </div>
    </div>
  )
}

export default Purchase

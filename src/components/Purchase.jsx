import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { loadCart } from '../cart'
import useInventory from '../useInventory'
import useQuote from '../useQuote'
import QuoteStatus from './QuoteStatus'
import InventoryStatus from './InventoryStatus'

const formatPrice = (amount) =>
  amount.toLocaleString('en-US', { style: 'currency', currency: 'USD' })

function Stepper({ value, min, max, onChange, label }) {
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
        max={max}
        aria-label={label}
        value={value}
        onChange={(event) => onChange(parseInt(event.target.value, 10) || min)}
      />
      <button type="button" aria-label={`Increase ${label}`} disabled={value >= max} onClick={() => onChange(value + 1)}>
        +
      </button>
    </div>
  )
}

function Purchase() {
  const navigate = useNavigate()
  const { products, loading, error, reload } = useInventory()
  const [cart, setCart] = useState(loadCart)
  const pricing = useQuote(cart)
  const { quote } = pricing
  const [pending, setPending] = useState({})
  const [justAdded, setJustAdded] = useState(null)

  const updateCart = (nextCart) => {
    setCart(nextCart)
    localStorage.setItem('cart', JSON.stringify(nextCart))
  }

  const setQuantity = (index, quantity) => {
    const nextCart = { ...cart }
    const stock = products.find(product => product.id === index)?.availableQty ?? 0
    nextCart[index] = Math.min(stock, Math.max(0, quantity || 0))
    updateCart(nextCart)
  }

  const setPendingQuantity = (index, quantity) => {
    const nextPending = { ...pending }
    nextPending[index] = Math.max(1, quantity)
    setPending(nextPending)
  }

  const addToCart = (index) => {
    setQuantity(index, (cart[index] || 0) + (pending[index] || 1))
    setPendingQuantity(index, 1)
    setJustAdded(index)
    setTimeout(() => setJustAdded((current) => (current === index ? null : current)), 1200)
  }

  const cartLines = products.filter((product) => cart[product.id] > 0)
  const itemCount = quote?.itemCount
  const cartIssue = !!quote?.unavailable.length
    || Object.keys(cart).some(id => cart[id] > 0 && !products.some(product => String(product.id) === id))

  const handleCheckout = (event) => {
    event.preventDefault()
    if (loading || error || !cartLines.length || cartIssue || !quote) return
    navigate('/purchase/paymentEntry')
  }

  return (
    <div className="purchase">
      <header className="shop-heading"><p className="eyebrow">FIND YOUR NEXT FAVORITE</p><h1 className="page-title">The Collection</h1><p>Distinctive pieces. Endless ways to make them your own.</p></header>

      <InventoryStatus loading={loading} error={error} reload={reload} />
      {!loading && !error && !products.length && <p role="status">No products are available right now.</p>}
      <div className="purchase-layout">
        <section className="catalog" aria-label="Products">
          {products.map((product) => (
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
                <p>{product.description}</p>
                <p>{product.availableQty > 0 ? `${product.availableQty} available` : 'Out of stock'}</p>
              </div>
              <div className="product-actions">
                <Stepper
                  label={`${product.name} quantity`}
                  min={1}
                  max={Math.max(1, product.availableQty - (cart[product.id] || 0))}
                  value={Math.min(pending[product.id] || 1, Math.max(1, product.availableQty - (cart[product.id] || 0)))}
                  onChange={(quantity) => setPendingQuantity(product.id, quantity)}
                />
                <button
                  type="button"
                  className="btn"
                  disabled={loading || !!error || (cart[product.id] || 0) >= product.availableQty}
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
              Your Bag <span className="cart-count">({itemCount ?? '…'})</span>
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
                        <span>{quote?.items.find(item => item.id === product.id) ? formatPrice(quote.items.find(item => item.id === product.id).subtotal) : '…'}</span>
                      </div>
                      <div className="cart-line-bottom">
                        <Stepper
                          label={`${product.name} quantity in bag`}
                          min={0}
                          max={product.availableQty}
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

            {!loading && !error && cartIssue && <p className="order-notice" role="alert">Some items are no longer available in the requested quantity. Adjust your bag or <button type="button" onClick={() => updateCart({})}>clear your bag</button>.</p>}
            <QuoteStatus {...pricing} />
            <div className="cart-total">
              <span>Total</span>
              <span>{quote ? formatPrice(quote.total) : '—'}</span>
            </div>

            <button
              type="submit"
              className="btn btn-primary btn-block"
              disabled={loading || !!error || cartIssue || !quote || cartLines.length === 0}
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

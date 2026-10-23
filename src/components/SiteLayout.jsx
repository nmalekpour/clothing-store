import { useEffect } from 'react'
import { Link, NavLink, useLocation } from 'react-router-dom'

const links = [['/', 'Home'], ['/purchase', 'Shop'], ['/about', 'About Us'], ['/contact', 'Contact Us']]

const steps = [
    ['/purchase', 'Bag'],
    ['/purchase/paymentEntry', 'Payment'],
    ['/purchase/shippingEntry', 'Shipping'],
    ['/purchase/viewOrder', 'Review'],
    ['/purchase/viewConfirmation', 'Confirmation'],
  ]
const currentYear = new Date().getFullYear()

export default function SiteLayout({ children }) {
  const { pathname, hash } = useLocation()
  const checkout = pathname.startsWith('/purchase/')


  useEffect(() => {
    const title = links.find(([path]) => path === pathname)?.[1]
      ?? steps.find(([path]) => path === pathname)?.[1] ?? 'Clothing Store'
    document.title = `${title} | Clothing Store`
    if (hash) {
      requestAnimationFrame(() => document.getElementById(hash.slice(1))?.scrollIntoView())
    } else {
      window.scrollTo(0, 0)
    }
  }, [pathname, hash])

  return (
    <>
      <a className="skip-link" href="#main-content">Skip to content</a>
      <div className="brand-note">A considered collection. A style of your own.</div>
      <header className="site-header">
        <div className="header-inner">
          <Link className="wordmark" to="/">Clothing Store<span>THE EVERYDAY EDIT</span></Link>
          <nav aria-label="Main navigation">
            {links.map(([path, label]) => <NavLink key={path} to={path} end={path === '/'}>{label}</NavLink>)}
          </nav>
        </div>
      </header>
      <main id="main-content" tabIndex={-1}>
        {checkout && <ol className="checkout-progress" aria-label="Checkout progress">
          {steps.map(([path, label], index) => <li key={path} aria-current={pathname === path ? 'step' : undefined}>
            <span>{index + 1}</span> {label}
          </li>)}
        </ol>}
        {children}
      </main>
      <footer className="site-footer">
        <div className="footer-inner">
          <div className="footer-brand"><Link className="wordmark" to="/">Clothing Store</Link><p>A considered collection of clothing<br />and accessories. Make it your own.</p></div>
          <div><h2>Explore</h2><Link to="/">Home</Link><Link to="/purchase">Shop the collection</Link><Link to="/about">About us</Link></div>
          <div><h2>Customer Care</h2><Link to="/contact">Contact us</Link><Link to="/contact#returns">Returns & support</Link><Link to="/contact#faq">Frequently asked questions</Link></div>
        </div>
        <div className="footer-bottom"><span>© {currentYear} Clothing Store</span><span>A considered collection. A style of your own.</span></div>
      </footer>
    </>
  )
}

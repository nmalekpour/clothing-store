import { Link } from 'react-router-dom'
import { PRODUCTS } from '../data/products'

export default function Home() {
  return (
    <div className="home-page">
      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">THE CLOTHING STORE EDIT</p>
          <h1>A considered wardrobe.<br /><em>A style of your own.</em></h1>
          <p>From effortless everyday pieces to elegant finishing touches. Discover clothing and accessories that make getting dressed feel like you.</p>
          <Link className="btn btn-primary" to="/purchase">Explore the collection <span aria-hidden="true">↗</span></Link>
          <span className="hero-caption">Simple pieces. Endless possibilities.</span>
        </div>
        <div className="hero-image"><img src="/images/sage-dress.jpeg" alt="Sage Dress from the Clothing Store collection" /><span>01 / THE SAGE DRESS</span></div>
      </section>

      <section className="featured-section" aria-labelledby="featured-heading">
        <div className="section-heading"><div><p className="eyebrow">A FEW FAVORITES</p><h2 id="featured-heading">The Selected Edit</h2></div><Link className="text-link" to="/purchase">View all five pieces <span aria-hidden="true">→</span></Link></div>
        <div className="featured-grid">
          {[PRODUCTS[0], PRODUCTS[2], PRODUCTS[4]].map((product) => <Link className="featured-product" to="/purchase" key={product.id}>
            <div className="product-image"><img src={product.image} alt={product.name} loading="lazy" /></div>
            <div><h3>{product.name}</h3><span>{product.price.toLocaleString('en-US', { style: 'currency', currency: 'USD' })}</span></div>
          </Link>)}
        </div>
      </section>

      <section className="philosophy">
        <p className="eyebrow">OUR PHILOSOPHY</p>
        <h2>Style is personal.<br />Your wardrobe should be, too.</h2>
        <p>A flowing dress. A classic coat. A finishing touch that brings it all together. We believe a thoughtful selection leaves more room for individual expression.</p>
        <Link className="text-link" to="/about">Discover our story <span aria-hidden="true">→</span></Link>
      </section>
      <div className="care-banner"><div><p className="eyebrow">HERE WHEN YOU NEED US</p><h2>A little help goes a long way.</h2></div><Link className="btn" to="/contact">Contact our team</Link></div>
    </div>
  )
}

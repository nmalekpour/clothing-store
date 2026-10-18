import { useState } from 'react'

export default function Contact() {
  const [submitted, setSubmitted] = useState(false)
  const handleSubmit = (event) => {
    event.preventDefault()
    setSubmitted(true)
  }

  return (
    <div className="contact-page">
      <header className="editorial-heading"><p className="eyebrow">CUSTOMER CARE</p><h1>A little help.<br /><em>A personal touch.</em></h1><p>Questions about an order, a return, or an item you received? Start here. Include your confirmation number so our team can understand your request.</p></header>
      <div className="contact-layout">
        <section className="support-info" aria-labelledby="support-heading"><p className="eyebrow">LET’S TALK</p><h2 id="support-heading">How can we help?</h2><p>For returns, damaged items, incorrect orders, or general product questions, contact our Customer Care team.</p><dl><dt>Customer Care email</dt><dd>Email contact details coming soon</dd><dt>Support hours</dt><dd>Monday–Friday, 9 AM–5 PM Central Time</dd><dt>Response time</dt><dd>Within two business days</dd></dl></section>
        <section className="contact-form-panel" aria-labelledby="form-heading"><h2 id="form-heading">Send an inquiry</h2><p className="form-intro">All fields are required unless marked optional.</p>
          <form onSubmit={handleSubmit} onChange={() => setSubmitted(false)}>
            <div className="contact-fields"><div><label htmlFor="contact-name">Name</label><input id="contact-name" name="name" autoComplete="name" required maxLength={100} pattern=".*\S.*" /></div><div><label htmlFor="contact-email">Email</label><input id="contact-email" name="email" type="email" autoComplete="email" required maxLength={254} /></div></div>
            <div><label htmlFor="contact-order">Confirmation number (optional)</label><input id="contact-order" name="order" type="text" placeholder="CS-XXXXXXXX" maxLength={50} /></div>
            <div><label htmlFor="contact-topic">Topic</label><select id="contact-topic" name="topic" defaultValue="" required><option value="" disabled>Select a topic</option><option>Return request</option><option>Damaged or incorrect item</option><option>Order question</option><option>Product question</option><option>Other</option></select></div>
            <div><label htmlFor="contact-message">Message</label><textarea id="contact-message" name="message" rows={5} required minLength={10} maxLength={3000} placeholder="Tell us how we can help (at least 10 characters)." /></div>
            <p className="form-intro" id="form-note">Online messaging is not yet available. You can check your inquiry details below, but they will not be sent.</p>
            <button className="btn btn-primary" type="submit" aria-describedby="form-note">Check inquiry <span aria-hidden="true">↗</span></button>
            <div role="status" className={submitted ? 'form-success' : ''}>{submitted && 'Your inquiry details are complete. Online messaging is not yet available; your inquiry has not been sent.'}</div>
          </form>
        </section>
      </div>
      <section className="returns-section" id="returns" aria-labelledby="returns-heading"><p className="eyebrow">AFTER YOUR PURCHASE</p><h2 id="returns-heading">Returns & order support</h2><div className="policy-grid"><article><h3>A 30-day return window</h3><p>Request a return within 30 days of delivery. Items should be unworn, unwashed, and have their original tags attached.</p></article><article><h3>Start with Customer Care</h3><p>Include your confirmation number and the items you wish to return. Wait for return instructions before shipping anything back. Return shipping costs and eligibility will be explained in those instructions.</p></article><article><h3>Something not quite right?</h3><p>For a damaged or incorrect item, describe the issue and include your confirmation number. Photos help our team assess the issue and review replacement or refund options with you.</p></article></div></section>
      <section className="faq-section" id="faq" aria-labelledby="faq-heading"><p className="eyebrow">GOOD TO KNOW</p><h2 id="faq-heading">Frequently asked questions</h2>
        <details><summary>Where can I find my confirmation number?</summary><p>Your confirmation number appears on the order confirmation page after you confirm your order. Keep a copy for future reference.</p></details>
        <details><summary>How do I request a return?</summary><p>Contact Customer Care with your confirmation number and the item names within 30 days of delivery. Ask for instructions before sending items back.</p></details>
        <details><summary>What if my item is damaged or incorrect?</summary><p>Contact Customer Care with your confirmation number and a description of the issue. For a real support request, photos help the team assess the problem.</p></details>
        <details><summary>Can I change my shipping address?</summary><p>Before confirming your order, use “Edit shipping” on the review page. After confirmation, contact Customer Care to ask whether a change is still possible.</p></details>

      </section>
    </div>
  )
}

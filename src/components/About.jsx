import { useState } from 'react'

const executives = [
  {
    number: '01',
    name: 'Iris Kuo',
    image: '/images/iris.jpg',
    role: 'Director of Payments & Engineering',
    education: 'MSCSE @ The Ohio State Univeristy',
    experience: 'AICure, Software Engineering Intern | 2026.05–2027.08\nMitac, Software Engineer | 2024.02–2025.01',
    passions: 'Iris enjoys building end-to-end products that connect intuitive interfaces with robust backend systems. Her interests span full-stack development, cloud infrastructure, and AI integration.',
  },
  {
    number: '02',
    name: 'Niki Malekpour',
    image: '/images/niki.jpg',
    role: 'Director of Product & Engineering',
    education: 'BSCSE @ The Ohio State University',
    experience: 'WillowTree, Software Engineering Intern | 2026.05–2026.08',
    passions: 'Niki enjoys full-stack development and building polished products from the interface down to the code behind it, with a strong focus on user experience and attention to detail.',
  },
  {
    number: '03',
    name: 'Anna Krivoy',
    image: '/images/anna.jpg',
    role: 'Director of Data and Engineering',
    education: 'BSCIS @ The Ohio State University',
    experience: 'Marathon Petroleum Corporation, Software Engineer Intern 2026.05-2026.08',
    passions: 'Anna is a software engineer with a passion for people, design, and high-level product thinking. She cares about building intentional products that solve real problems and spark a little joy along the way.',
  },
]

function TeamPortrait({ person }) {
  const [failed, setFailed] = useState(false)

  if (person.image && !failed) {
    return <img className="team-portrait" src={person.image} alt={`${person.name}, ${person.role}`} loading="lazy" onError={() => setFailed(true)} />
  }

  return <div className="portrait-placeholder"><span aria-hidden="true">{person.name?.charAt(0) || person.number}</span><p>{person.name ? `${person.name} · Photo coming soon` : 'Team member photo'}</p></div>
}

export default function About() {
  return (
    <div className="about-page">
      <header className="editorial-heading"><p className="eyebrow">GET TO KNOW US</p><h1>A thoughtful edit.<br /><em>A shared vision.</em></h1><p>Clothing Store brings together thoughtfully selected clothing and accessories, connecting everyday simplicity with individual expression.</p></header>
      <section className="story-grid" aria-labelledby="story-heading">
        <div className="story-image"><img src="/images/coat.jpeg" alt="Classic Peacoat from our collection" loading="lazy" /></div>
        <div className="story-copy"><p className="eyebrow">OUR STORY</p><h2 id="story-heading">Fewer distractions.<br />More personal style.</h2><p>Our collection brings together clothing and accessories that can stand on their own or work together: a simple white tank, wide-leg pants, a flowing sage dress, a classic peacoat, and a distinctive necklace.</p><p>We built this store around clear product presentation and an easy-to-follow shopping journey, giving every piece room to speak for itself.</p></div>
      </section>
      <section className="values-grid" aria-label="Mission, vision, and strategy">
        <article><p className="eyebrow">01 / OUR MISSION</p><h2>Confidence, every day.</h2><p>To help customers express their personal style through a considered selection of clothing and accessories and an approachable shopping experience.</p></article>
        <article><p className="eyebrow">02 / OUR VISION</p><h2>A place to find your style.</h2><p>To become a trusted fashion destination where customers can discover pieces that complement their lives and feel distinctly their own.</p></article>
        <article><p className="eyebrow">03 / OUR STRATEGY</p><h2>Thoughtful at every step.</h2><p>We focus on a concise collection, clear product information, and consistent service. Listening to customer feedback will guide improvements to our selection and shopping experience.</p></article>
      </section>
      <section className="team-section" aria-labelledby="team-heading">
        <div className="section-heading"><div><p className="eyebrow">THE PEOPLE BEHIND THE VISION</p><h2 id="team-heading">Meet Our Executives</h2></div></div>
        <div className="team-grid">{executives.map((person) => <article className="team-card" key={person.number}>
          <TeamPortrait person={person} />
          <p className="eyebrow">{person.role}</p>
          <h3>{person.name || `[Team Member ${person.number} Name]`}</h3>
          <dl className="team-details">
            <dt>Education</dt><dd>{person.education}</dd>
            <dt>Experience</dt><dd>{person.experience}</dd>
            <dt>Passions</dt><dd>{person.passions}</dd>
          </dl>
        </article>)}</div>
      </section>
    </div>
  )
}

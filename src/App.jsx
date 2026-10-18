import { Route, Routes } from 'react-router-dom'
import SiteLayout from './components/SiteLayout'
import Home from './components/Home'
import About from './components/About'
import Contact from './components/Contact'
import Purchase from './components/Purchase'
import PaymentEntry from './components/PaymentEntry'
import ShippingEntry from './components/ShippingEntry'
import ViewOrder from './components/ViewOrder'
import Confirmation from './components/Confirmation'

function App() {
  return (
    <SiteLayout>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/about" element={<About />} />
        <Route path="/contact" element={<Contact />} />
        <Route path="/purchase" element={<Purchase />} />
        <Route path="/purchase/paymentEntry" element={<PaymentEntry />} />
        <Route path="/purchase/shippingEntry" element={<ShippingEntry />} />
        <Route path="/purchase/viewOrder" element={<ViewOrder />} />
        <Route path="/purchase/viewConfirmation" element={<Confirmation />} />
      </Routes>
    </SiteLayout>
  )
}

export default App

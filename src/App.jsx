import { Navigate, Route, Routes } from 'react-router-dom'
import Purchase from './components/Purchase'
import PaymentEntry from './components/PaymentEntry'
import ShippingEntry from './components/ShippingEntry'
import ViewOrder from './components/ViewOrder'
import Confirmation from './components/Confirmation'

function App() {
  return (
    <main>
      <Routes>
        <Route path="/" element={<Navigate to="/purchase" replace />} />
        <Route path="/purchase" element={<Purchase />} />
        <Route path="/purchase/paymentEntry" element={<PaymentEntry />} />
        <Route path="/purchase/shippingEntry" element={<ShippingEntry />} />
        <Route path="/purchase/viewOrder" element={<ViewOrder />} />
        <Route path="/purchase/viewConfirmation" element={<Confirmation />} />
      </Routes>
    </main>
  )
}

export default App

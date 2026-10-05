import { useNavigate } from 'react-router-dom'

function PaymentEntry() {
  const navigate = useNavigate()

  return (
    <div>
      <h1>Payment</h1>
      {/* TODO */}
      <button onClick={() => navigate('/purchase/shippingEntry')}>Next</button>
    </div>
  )
}

export default PaymentEntry

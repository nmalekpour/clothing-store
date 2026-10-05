import { useNavigate } from 'react-router-dom'

function ShippingEntry() {
  const navigate = useNavigate()

  return (
    <div>
      <h1>Shipping</h1>
      {/* TODO */}
      <button onClick={() => navigate('/purchase/viewOrder')}>Next</button>
    </div>
  )
}

export default ShippingEntry

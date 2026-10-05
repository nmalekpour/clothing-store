import { useNavigate } from 'react-router-dom'

function Purchase() {
  const navigate = useNavigate()

  return (
    <div>
      <h1>Shop</h1>
      {/* TODO */}
      <button onClick={() => navigate('/purchase/paymentEntry')}>Next</button>
    </div>
  )
}

export default Purchase

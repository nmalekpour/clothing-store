import { useNavigate } from 'react-router-dom'

function ViewOrder() {
  const navigate = useNavigate()

  return (
    <div>
      <h1>Review Your Order</h1>
      {/* TODO */}
      <button onClick={() => navigate('/purchase/viewConfirmation')}>Next</button>
    </div>
  )
}

export default ViewOrder

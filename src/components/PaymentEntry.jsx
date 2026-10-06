import { useNavigate } from 'react-router-dom'
import { useState } from 'react'

function PaymentEntry() {
  const navigate = useNavigate()

  const [paymentInfo, setPaymentInfo] = useState(() => {
    const savedPayment = localStorage.getItem('paymentInfo')

    return savedPayment
      ? JSON.parse(savedPayment)
      : {
          cardholderName: '',
          cardNumber: '',
          expirationDate: '',
          cvv: '',
          billingZip: '',
        }
  })

  const handleChange = (event) => {
    const { name, value } = event.target

    setPaymentInfo((previous) => ({
      ...previous,
      [name]: value,
    }))
  }

  const handleSubmit = (event) => {
    event.preventDefault()

    localStorage.setItem('paymentInfo', JSON.stringify(paymentInfo))

    alert('Payment information saved!')
  }

  const handleClear = () => {
    const emptyPayment = {
      cardholderName: '',
      cardNumber: '',
      expirationDate: '',
      cvv: '',
      billingZip: '',
    }

    setPaymentInfo(emptyPayment)
    localStorage.removeItem('paymentInfo')
  }

  const handleContinue = () => {
    localStorage.setItem('paymentInfo', JSON.stringify(paymentInfo))
    navigate('/purchase/shippingEntry')
  }

  return (
    <div className="payment-entry">
      <h2>Payment Information</h2>

      <form onSubmit={handleSubmit}>
        <div>
          <label htmlFor="cardholderName">Cardholder Name</label>
          <input
            id="cardholderName"
            type="text"
            name="cardholderName"
            value={paymentInfo.cardholderName}
            onChange={handleChange}
            placeholder="John Doe"
            required
          />
        </div>

        <div>
          <label htmlFor="cardNumber">Card Number</label>
          <input
            id="cardNumber"
            type="text"
            name="cardNumber"
            value={paymentInfo.cardNumber}
            onChange={handleChange}
            placeholder="1234 5678 9012 3456"
            maxLength="19"
            required
          />
        </div>

        <div>
          <label htmlFor="expirationDate">Expiration Date</label>
          <input
            id="expirationDate"
            type="text"
            name="expirationDate"
            value={paymentInfo.expirationDate}
            onChange={handleChange}
            placeholder="MM/YY"
            maxLength="5"
            required
          />
        </div>

        <div>
          <label htmlFor="cvv">CVV</label>
          <input
            id="cvv"
            type="text"
            name="cvv"
            value={paymentInfo.cvv}
            onChange={handleChange}
            placeholder="123"
            maxLength="4"
            required
          />
        </div>

        <div>
          <label htmlFor="billingZip">Billing ZIP Code</label>
          <input
            id="billingZip"
            type="text"
            name="billingZip"
            value={paymentInfo.billingZip}
            onChange={handleChange}
            placeholder="43210"
            maxLength="5"
            required
          />
        </div>

        <button type="submit">
          Save Payment
        </button>

        <button type="button" onClick={handleClear}>
          Clear Payment
        </button>

        <button type="button" onClick={handleContinue}>
          Continue to Shipping
        </button>
      </form>
    </div>
  )
}

export default PaymentEntry
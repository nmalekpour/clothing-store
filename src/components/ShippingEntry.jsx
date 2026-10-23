import { useNavigate } from 'react-router-dom'
import { useState } from 'react'

function ShippingEntry() {
  const navigate = useNavigate()

  const emptyAddress = {
    name: '',
    fullName: '',
    address: '',
    apartment: '',
    city: '',
    state: '',
    zip: '',
  }

  const [address, setAddress] = useState(() => {
    try { return JSON.parse(localStorage.getItem('selectedShippingAddress')) || emptyAddress }
    catch { return emptyAddress }
  })

  const [savedAddresses, setSavedAddresses] = useState(() => {
    const saved = localStorage.getItem('shippingAddresses')

    return saved ? JSON.parse(saved) : []
  })

  const handleChange = (event) => {
    const { name, value } = event.target

    setAddress((previous) => ({
      ...previous,
      [name]: value,
    }))
  }

  const handleSaveAddress = (event) => {
    event.preventDefault()

    const newAddress = {
      ...address,
      id: Date.now(),
    }

    const updatedAddresses = [...savedAddresses, newAddress]

    setSavedAddresses(updatedAddresses)

    localStorage.setItem(
      'shippingAddresses',
      JSON.stringify(updatedAddresses)
    )

    alert('Address saved!')

    setAddress(newAddress)
  }

  const handleSelectAddress = (savedAddress) => {
    setAddress(savedAddress)
  }

  const handleDeleteAddress = (id) => {
    const updatedAddresses = savedAddresses.filter(
      (savedAddress) => savedAddress.id !== id
    )

    setSavedAddresses(updatedAddresses)

    localStorage.setItem(
      'shippingAddresses',
      JSON.stringify(updatedAddresses)
    )
  }

  const handleContinue = () => {
    if (!document.getElementById('shipping-form').reportValidity()) return
    localStorage.setItem('selectedShippingAddress', JSON.stringify(address))

    navigate('/purchase/viewOrder')
  }

  return (
    <div className="shipping-entry">
      <h2>Shipping Information</h2>

      <form id="shipping-form" onSubmit={handleSaveAddress}>
        <div>
          <label htmlFor="name">Address Name</label>
          <input
            id="name"
            type="text"
            name="name"
            value={address.name}
            onChange={handleChange}
            placeholder="Home, Dorm, Parents' House..."
            required
          />
        </div>

        <div>
          <label htmlFor="fullName">Full Name</label>
          <input
            id="fullName"
            type="text"
            name="fullName"
            value={address.fullName}
            onChange={handleChange}
            placeholder="John Doe"
            required
          />
        </div>

        <div>
          <label htmlFor="address">Street Address</label>
          <input
            id="address"
            type="text"
            name="address"
            value={address.address}
            onChange={handleChange}
            placeholder="123 Main Street"
            required
          />
        </div>

        <div>
          <label htmlFor="apartment">Apartment / Unit</label>
          <input
            id="apartment"
            type="text"
            name="apartment"
            value={address.apartment}
            onChange={handleChange}
            placeholder="Apt 4B"
          />
        </div>

        <div>
          <label htmlFor="city">City</label>
          <input
            id="city"
            type="text"
            name="city"
            value={address.city}
            onChange={handleChange}
            placeholder="Columbus"
            required
          />
        </div>

        <div>
          <label htmlFor="state">State</label>
          <input
            id="state"
            type="text"
            name="state"
            value={address.state}
            onChange={handleChange}
            placeholder="OH"
            maxLength="2"
            required
          />
        </div>

        <div>
          <label htmlFor="zip">ZIP Code</label>
          <input
            id="zip"
            type="text"
            name="zip"
            value={address.zip}
            onChange={handleChange}
            placeholder="43210"
            maxLength="5"
            required
          />
        </div>

        <button type="submit">
          Save Address
        </button>
      </form>

      <hr />

      <h3>Saved Addresses</h3>

      {savedAddresses.length === 0 ? (
        <p>No saved addresses yet.</p>
      ) : (
        <div>
          {savedAddresses.map((savedAddress) => (
            <div key={savedAddress.id}>
              <h4>{savedAddress.name}</h4>

              <p>
                {savedAddress.fullName}
                <br />
                {savedAddress.address}
                {savedAddress.apartment && (
                  <>
                    <br />
                    {savedAddress.apartment}
                  </>
                )}
                <br />
                {savedAddress.city}, {savedAddress.state}{' '}
                {savedAddress.zip}
              </p>

              <button
                type="button"
                onClick={() => handleSelectAddress(savedAddress)}
              >
                Use This Address
              </button>

              <button
                type="button"
                onClick={() => handleDeleteAddress(savedAddress.id)}
              >
                Delete
              </button>
            </div>
          ))}
        </div>
      )}

      <br />

      <button type="button" onClick={handleContinue}>
        Continue to View Order
      </button>
    </div>
  )
}

export default ShippingEntry
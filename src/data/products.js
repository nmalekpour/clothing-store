// Catalog shared by every page. Index in this array === index in order.buyQuantity.
// Put image files in public/images/ (paths below are served from the site root).
export const PRODUCTS = [
  { id: 0, name: 'Sage Dress', price: 280.00, image: '/images/sage-dress.jpeg' },
  { id: 1, name: 'White Tank', price: 90.00, image: '/images/white-tank.jpeg' },
  { id: 2, name: 'Peacoat', price: 550.00, image: '/images/coat.jpeg' },
  { id: 3, name: 'Wide-Leg Pants', price: 148.00, image: '/images/pants.png' },
  { id: 4, name: 'Diamond Lariat Necklace', price: 1200.00, image: '/images/necklace.png' },
]

export function emptyOrder() {
  return {
    buyQuantity: PRODUCTS.map(() => 0),
    credit_card_number: '',
    expir_date: '',
    cvvCode: '',
    card_holder_name: '',
    name: '',
    address_1: '',
    address_2: '',
    city: '',
    state: '',
    zip: '',
  }
}

// Filled-in sample so pages later in the flow can be built before Purchase is done.
export const MOCK_ORDER = {
  buyQuantity: [1, 2, 0, 1, 0],
  credit_card_number: '4111111111111111',
  expir_date: '12/27',
  cvvCode: '123',
  card_holder_name: 'Jane Doe',
  name: 'Jane Doe',
  address_1: '123 Main St',
  address_2: 'Apt 4',
  city: 'Columbus',
  state: 'OH',
  zip: '43210',
}

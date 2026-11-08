import axios from 'axios'

export const api = axios.create({
  baseURL: import.meta.env?.VITE_API_BASE_URL,
  timeout: 30000,
})

export async function getInventory(signal) {
  const { data } = await api.get('/inventory-management/inventory', { signal })
  if (!Array.isArray(data) || data.some(item =>
    !item || !Number.isSafeInteger(item.id) || item.id < 0 || typeof item.name !== 'string'
    || !Number.isFinite(item.price) || item.price < 0
    || typeof item.description !== 'string' || typeof item.image !== 'string'
    || !Number.isSafeInteger(item.availableQty) || item.availableQty < 0)
    || new Set(data.map(item => item.id)).size !== data.length) {
    throw new Error('The inventory service returned invalid product data.')
  }
  return data
}

function orderItems(items) {
  return items.map(({ id, quantity }) => ({ id: Number(id), quantity }))
}

function validateQuote(data) {
  if (!data || !Array.isArray(data.items) || !Array.isArray(data.unavailable)
    || !Number.isFinite(data.total) || data.total < 0
    || !Number.isSafeInteger(data.itemCount) || data.itemCount < 0
    || data.items.some(item => !item || !Number.isSafeInteger(item.id)
      || typeof item.name !== 'string' || typeof item.image !== 'string'
      || !Number.isSafeInteger(item.quantity) || item.quantity <= 0
      || !Number.isFinite(item.price) || item.price < 0
      || !Number.isFinite(item.subtotal) || item.subtotal < 0)) {
    throw new Error('The order service returned invalid pricing data.')
  }
  return data
}

export async function getQuote(items, signal) {
  // No payment or shipping is sent for a non-mutating preview.
  const { data } = await api.post('/order-processing/order', {
    preview: true, items: orderItems(items),
  }, { signal })
  if (data?.confirmationNumber) throw new Error('Unexpected order confirmation during preview.')
  return validateQuote(data)
}

export async function submitOrder({ items, payment, shipping, expectedTotal }) {
  const { data } = await api.post('/order-processing/order', {
    items: orderItems(items), payment, shipping, expectedTotal,
  })
  if (typeof data?.confirmationNumber !== 'string' || !data.confirmationNumber.trim()) {
    throw new Error('The order service did not return a confirmation number. Check your order before trying again.')
  }
  return validateQuote(data)
}

export function errorMessage(error, fallback) {
  return typeof error.response?.data?.error === 'string'
    ? error.response.data.error
    : error.message === 'Network Error' || error.code === 'ECONNABORTED'
      ? 'Unable to reach the service. Check your connection and try again.'
      : fallback
}

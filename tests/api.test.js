import test from 'node:test'
import assert from 'node:assert/strict'
import { api, getInventory, getQuote, submitOrder } from '../src/api.js'
import { loadCart } from '../src/cart.js'

const product = { id: 42, name: 'Service product', price: 17.5, description: 'From API', image: '/test.jpg', availableQty: 3 }
const quote = { items: [{ ...product, quantity: 2, subtotal: 35 }], total: 35, itemCount: 2, unavailable: [] }
const respond = data => async config => ({ data, status: 200, statusText: 'OK', headers: {}, config })

test('inventory accepts service IDs and rejects malformed or duplicate products', async () => {
  api.defaults.adapter = respond([product])
  assert.deepEqual(await getInventory(), [product])
  for (const data of [[null], [{ ...product, availableQty: -1 }], [product, product], { items: [product] }]) {
    api.defaults.adapter = respond(data)
    await assert.rejects(getInventory(), /invalid product data/)
  }
})

test('checkout sends only numeric IDs and quantities, and returns the backend confirmation', async () => {
  api.defaults.adapter = async config => {
    assert.equal(config.url, '/order-processing/order')
    assert.deepEqual(JSON.parse(config.data), {
      items: [{ id: 42, quantity: 2 }], payment: { cardholderName: 'Test' }, shipping: { fullName: 'Test' }, expectedTotal: 35,
    })
    return respond({ ...quote, confirmationNumber: 'BACKEND-42' })(config)
  }
  assert.deepEqual(await submitOrder({
    items: [{ ...product, id: '42', quantity: 2, subtotal: 35 }],
    payment: { cardholderName: 'Test' }, shipping: { fullName: 'Test' }, expectedTotal: 35,
  }), { ...quote, confirmationNumber: 'BACKEND-42' })
})

test('checkout rejects a success response without a confirmation number', async () => {
  api.defaults.adapter = respond({})
  await assert.rejects(submitOrder({ items: [], payment: {}, shipping: {} }), /confirmation number/)
})

test('cart restores old arrays and keyed IDs while rejecting invalid stored quantities', () => {
  globalThis.localStorage = { getItem: () => '[0,2,0,1]' }
  assert.deepEqual(loadCart(), { 1: 2, 3: 1 })
  globalThis.localStorage.getItem = () => '{"42":2,"91":0,"5":-1,"6":1.5,"bad":3}'
  assert.deepEqual(loadCart(), { 42: 2 })
  globalThis.localStorage.getItem = () => 'invalid JSON'
  assert.deepEqual(loadCart(), {})
  delete globalThis.localStorage
})


test('price preview sends no payment or shipping and uses server totals unchanged', async () => {
  api.defaults.adapter = async config => {
    assert.deepEqual(JSON.parse(config.data), { preview: true, items: [{ id: 42, quantity: 2 }] })
    return respond({ ...quote, total: 31.25 })(config)
  }
  assert.equal((await getQuote([{ id: 42, quantity: 2 }])).total, 31.25)
})

test('pricing rejects old deployments and malformed totals instead of inventing prices', async () => {
  api.defaults.adapter = respond({ confirmationNumber: 'OLD-SERVICE' })
  await assert.rejects(getQuote([]), /Unexpected order confirmation/)
  await assert.rejects(submitOrder({ items: [], payment: {}, shipping: {} }), /invalid pricing data/)
  api.defaults.adapter = respond({ ...quote, total: -1 })
  await assert.rejects(getQuote([]), /invalid pricing data/)
})

export function readSavedValue(key, fallback) {
  try {
    return JSON.parse(localStorage.getItem(key)) ?? fallback
  } catch {
    return fallback
  }
}

// Accept the previous array format, but store quantities by product ID.
export function loadCart() {
  const saved = readSavedValue('cart', {})
  if (!saved || typeof saved !== 'object') return {}
  return Object.fromEntries(Object.entries(saved).filter(([id, quantity]) =>
    /^\d+$/.test(id) && Number.isSafeInteger(quantity) && quantity > 0))
}

import { useCallback, useEffect, useState } from 'react'
import { errorMessage, getInventory } from './api'

export default function useInventory() {
  const [products, setProducts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [version, setVersion] = useState(0)
  const reload = useCallback(() => {
    setLoading(true)
    setError('')
    setVersion(value => value + 1)
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    getInventory(controller.signal).then(data => {
      if (!controller.signal.aborted) setProducts(data)
    }).catch(cause => {
      if (!controller.signal.aborted) {
        setError(errorMessage(cause, 'Unable to load products. Please try again.'))
      }
    }).finally(() => {
      if (!controller.signal.aborted) setLoading(false)
    })
    return () => controller.abort()
  }, [version])

  return { products, loading, error, reload }
}

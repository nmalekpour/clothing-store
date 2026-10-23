import { useCallback, useEffect, useState } from 'react'
import { errorMessage, getQuote } from './api'

export default function useQuote(cart) {
  const request = JSON.stringify(Object.entries(cart)
    .filter(([, quantity]) => quantity > 0)
    .map(([id, quantity]) => ({ id: Number(id), quantity })))
  const [version, setVersion] = useState(0)
  const key = `${version}:${request}`
  const [result, setResult] = useState({})
  const reload = useCallback(() => setVersion(value => value + 1), [])

  useEffect(() => {
    const controller = new AbortController()
    // Delay rapid quantity edits; abort obsolete responses so stale totals cannot be confirmed.
    const timer = setTimeout(() => {
      getQuote(JSON.parse(request), controller.signal).then(quote => {
        if (!controller.signal.aborted) setResult({ key, quote })
      }).catch(cause => {
        if (!controller.signal.aborted) {
          setResult({ key, error: errorMessage(cause, 'Unable to calculate your total. Please try again.') })
        }
      })
    }, 200)
    return () => { clearTimeout(timer); controller.abort() }
  }, [key, request])

  return {
    quote: result.key === key ? result.quote : null,
    loading: result.key !== key,
    error: result.key === key ? result.error : '',
    reload,
  }
}

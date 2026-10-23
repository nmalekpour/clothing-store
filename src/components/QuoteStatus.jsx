export default function QuoteStatus({ loading, error, reload }) {
  if (loading) return <p className="order-notice" role="status">Checking availability and calculating your total…</p>
  if (error) return <div className="order-notice" role="alert"><p>{error}</p><button type="button" onClick={reload}>Retry total</button></div>
  return null
}

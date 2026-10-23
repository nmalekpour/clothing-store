export default function InventoryStatus({ loading, error, reload }) {
  if (loading) return <p className="order-notice" role="status">Loading products…</p>
  if (error) return <div className="order-notice" role="alert"><p>{error}</p><button type="button" onClick={reload}>Retry</button></div>
  return null
}

import { useEffect, useState } from 'react'

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://127.0.0.1:8001'

const defaultQuery = {
  region: 'North America',
  line_of_business: 'Property',
  keywords: ['catastrophe', 'pricing'],
}

function App() {
  const [pricingResult, setPricingResult] = useState(null)
  const [marketSignal, setMarketSignal] = useState(null)
  const [aiInsight, setAiInsight] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    async function loadData() {
      setLoading(true)
      try {
        const [pricingRes, marketRes, aiRes] = await Promise.all([
          fetch(`${BACKEND_URL}/api/pricing/calculate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              treaty_id: 'TRT-2024-001',
              client_name: 'Acentria Reinsurance',
              effective_date: '2024-01-01',
              historical_losses: [
                { year: 2020, reported_loss: 1800000.0, paid_loss: 1500000.0, premium: 2400000.0 },
                { year: 2021, reported_loss: 2200000.0, paid_loss: 1800000.0, premium: 2600000.0 },
                { year: 2022, reported_loss: 2000000.0, paid_loss: 1700000.0, premium: 2500000.0 },
              ],
              layer_attachment: 1000000.0,
              layer_limit: 5000000.0,
              target_loss_ratio: 0.65,
              expenses_ratio: 0.20,
              profit_margin: 0.15,
            }),
          }).then((r) => r.json()),
          fetch(`${BACKEND_URL}/api/market/signal`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(defaultQuery),
          }).then((r) => r.json()),
          fetch(`${BACKEND_URL}/api/ai/insight`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(defaultQuery),
          }).then((r) => r.json()),
        ])
        setPricingResult(pricingRes)
        setMarketSignal(marketRes)
        setAiInsight(aiRes)
      } catch (error) {
        console.error(error)
      } finally {
        setLoading(false)
      }
    }

    loadData()
  }, [])

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">RMIP-DSS</div>
        <nav>
          <a href="#overview">Overview</a>
          <a href="#market">Market</a>
          <a href="#ai">AI</a>
        </nav>
      </aside>
      <main>
        <header>
          <h1>Acentria Reinsurance Dashboard</h1>
          <p>Market intelligence, pricing analytics, and portfolio insight.</p>
        </header>
        <section id="overview" className="panel">
          <h2>Overview</h2>
          <div className="cards">
            <div className="card">Gross Written Premium<br />USD 1.87B</div>
            <div className="card">Net Earned Premium<br />USD 1.32B</div>
            <div className="card">Combined Ratio<br />89.4%</div>
          </div>
        </section>
        <section id="market" className="panel">
          <h2>Market Signal</h2>
          {loading ? (
            <p>Loading market data...</p>
          ) : (
            <pre>{JSON.stringify(marketSignal, null, 2)}</pre>
          )}
        </section>
        <section id="pricing" className="panel">
          <h2>Live Pricing Result</h2>
          {loading ? (
            <p>Loading pricing result...</p>
          ) : (
            <pre>{JSON.stringify(pricingResult, null, 2)}</pre>
          )}
        </section>
        <section id="ai" className="panel">
          <h2>AI Insight</h2>
          {loading ? <p>Loading AI insight...</p> : <pre>{JSON.stringify(aiInsight, null, 2)}</pre>}
        </section>
      </main>
    </div>
  )
}

export default App

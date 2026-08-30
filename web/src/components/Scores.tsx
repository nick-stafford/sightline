import type { Altman, Piotroski } from '../types'

// The meter runs 0 to 8 with the published zone boundaries at 1.1 and 2.6.
// Anything above 8 pins to the end rather than rescaling the axis, so the zone
// bands stay in the same place from year to year.
const METER_MAX = 8
const DISTRESS_MAX = 1.1
const GREY_MAX = 2.6

export function AltmanCard({ altman }: { altman: Altman | null }) {
  if (!altman) {
    return (
      <div className="card">
        <h3>Altman Z''-Score</h3>
        <p className="empty-state">Not enough data in this year to compute the score.</p>
      </div>
    )
  }

  const position = Math.min(Math.max(altman.score, 0), METER_MAX) / METER_MAX

  return (
    <div className="card">
      <div className="score-header">
        <span className="score-value">{altman.score.toFixed(2)}</span>
        <span className={`zone-tag zone-${altman.zone}`}>{altman.zone}</span>
      </div>
      <p className="note" style={{ margin: 0, fontSize: 13, color: 'var(--text-secondary)' }}>
        Altman Z''-Score, the variant built for non-manufacturers. Weighs working
        capital, retained earnings, operating profitability and equity cover into a
        single distress measure.
      </p>

      <div style={{ position: 'relative' }}>
        <div className="meter">
          <span style={{ flex: DISTRESS_MAX, background: 'var(--critical)', opacity: 0.75 }} />
          <span style={{ width: 2, background: 'var(--surface)' }} />
          <span style={{ flex: GREY_MAX - DISTRESS_MAX, background: 'var(--warning)', opacity: 0.75 }} />
          <span style={{ width: 2, background: 'var(--surface)' }} />
          <span style={{ flex: METER_MAX - GREY_MAX, background: 'var(--good)', opacity: 0.75 }} />
          <span className="meter-marker" style={{ left: `${position * 100}%` }} />
        </div>
        <div className="meter-scale">
          <span>0</span>
          <span>1.1 distress</span>
          <span>2.6 safe</span>
          <span>8+</span>
        </div>
      </div>

      <table className="component-table">
        <thead>
          <tr>
            <th>Component</th>
            <th>Value</th>
            <th>Weight</th>
            <th>Contribution</th>
          </tr>
        </thead>
        <tbody>
          {altman.components.map((c) => (
            <tr key={c.key}>
              <td>{c.label}</td>
              <td>{c.value.toFixed(3)}</td>
              <td>{c.weight.toFixed(2)}</td>
              <td>{c.contribution.toFixed(2)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function PiotroskiCard({ piotroski }: { piotroski: Piotroski | null }) {
  if (!piotroski) {
    return (
      <div className="card">
        <h3>Piotroski F-Score</h3>
        <p className="empty-state">
          Needs a prior year to compare against, so the first year in the data has no
          score.
        </p>
      </div>
    )
  }

  const categories = ['Profitability', 'Leverage', 'Efficiency']

  return (
    <div className="card">
      <div className="score-header">
        <span className="score-value">
          {piotroski.score}
          <span style={{ fontSize: 20, color: 'var(--text-muted)' }}>/{piotroski.max}</span>
        </span>
        <span className="zone-tag zone-grey">{piotroski.band}</span>
      </div>
      <p style={{ margin: '0 0 6px', fontSize: 13, color: 'var(--text-secondary)' }}>
        Piotroski F-Score. Nine pass/fail tests of fundamental quality, one point each.
      </p>

      {categories.map((category) => (
        <div className="signal-group" key={category}>
          <h4>{category}</h4>
          {piotroski.signals
            .filter((s) => s.category === category)
            .map((signal) => (
              <div className="signal" key={signal.key}>
                <span className={`signal-mark ${signal.passed ? 'pass' : 'fail'}`}>
                  {signal.passed ? '✓' : '✕'}
                </span>
                <span className="signal-body">
                  <span className="signal-label">{signal.label}</span>
                  <br />
                  <span className="signal-detail">{signal.detail}</span>
                </span>
              </div>
            ))}
        </div>
      ))}
    </div>
  )
}

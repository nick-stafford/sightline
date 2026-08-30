import type { PeerData } from '../types'
import { byFormat } from '../format'

interface Props {
  peers: PeerData
  subject: string
}

/**
 * Percentile position within the cohort, one row per metric.
 *
 * Emphasis rather than categorical color: the subject company is the point, the
 * other seven are context, so they share a single neutral gray. Giving eight
 * companies eight hues would bury the one line the reader is here for.
 */
export function PeerChart({ peers, subject }: Props) {
  return (
    <div className="card">
      {peers.highlights.map((highlight) => {
        const rows = peers.ranks.filter((r) => r.metric === highlight.key)
        if (rows.length === 0) return null

        const subjectRow = rows.find((r) => r.ticker === subject)
        const others = rows.filter((r) => r.ticker !== subject)

        return (
          <div className="peer-row" key={highlight.key}>
            <div className="peer-label">{highlight.label}</div>

            <div className="peer-track">
              {others.map((row) => (
                <span
                  key={row.ticker}
                  className="peer-dot peer"
                  style={{ left: `${row.percentile * 100}%` }}
                  title={`${row.name}: ${byFormat(row.value, highlight.format)}`}
                />
              ))}
              {subjectRow && (
                <span
                  className="peer-dot subject"
                  style={{ left: `${subjectRow.percentile * 100}%` }}
                  title={`${subjectRow.name}: ${byFormat(subjectRow.value, highlight.format)}`}
                />
              )}
            </div>

            <div className="peer-value">
              {subjectRow ? byFormat(subjectRow.value, highlight.format) : '—'}
              <small>
                {subjectRow ? `${Math.round(subjectRow.percentile * 100)}th pct` : ''}
              </small>
            </div>
          </div>
        )
      })}

      <div className="legend">
        <span>
          <i style={{ background: 'var(--series-1)' }} /> {subject}
        </span>
        <span>
          <i style={{ background: 'var(--axis)' }} /> Peer company
        </span>
        <span style={{ color: 'var(--text-muted)' }}>
          Left is worse, right is better. Leverage and working capital days are
          inverted so that holds for every row.
        </span>
      </div>
    </div>
  )
}

import type { Flag } from '../types'

export function FlagList({ flags, fy }: { flags: Flag[]; fy: number }) {
  if (flags.length === 0) {
    return (
      <p className="empty-state">
        No rules triggered in FY{fy}. The ten checks cover inventory and receivables
        against sales, cash conversion, margin compression, coverage, leverage and
        accruals.
      </p>
    )
  }

  return (
    <div>
      {flags.map((flag) => (
        <div className={`flag ${flag.severity}`} key={flag.key}>
          <div className="flag-head">
            <h4>{flag.title}</h4>
            <span className={`severity ${flag.severity}`}>{flag.severity}</span>
          </div>
          <p>{flag.summary}</p>
          <div className="evidence">
            {flag.evidence.map((item) => (
              <div key={item.label}>
                <span className="label">{item.label}</span>
                <span className="value">{item.value}</span>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

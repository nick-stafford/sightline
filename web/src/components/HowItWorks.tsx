import { useState } from 'react'
import type { Meta } from '../types'

export interface CodeSample {
  key: string
  label: string
  language: string
  caption: string
  source: string
}

const STEPS = [
  {
    num: '01',
    title: 'Ingest',
    body: "Pull raw XBRL company facts for eight companies from the SEC's EDGAR API and cache them, so every later run is offline and reproducible.",
  },
  {
    num: '02',
    title: 'Normalize',
    body: 'Map the us-gaap tags to line items, keep only annual 10-K figures, prefer the most recent restatement, and fill gaps from fallback tags.',
  },
  {
    num: '03',
    title: 'Model in SQL',
    body: 'Load into DuckDB, pivot to one row per company-year, then build the ratio layer with window functions and rank against the cohort.',
  },
  {
    num: '04',
    title: 'Score and publish',
    body: 'Run the distress and quality models plus the rule engine in Python, write the analysis, and emit static JSON the page reads.',
  },
]

interface Props {
  meta: Meta | null
  samples: CodeSample[]
}

export function HowItWorks({ meta, samples }: Props) {
  const [active, setActive] = useState(samples[0]?.key ?? '')
  const current = samples.find((s) => s.key === active) ?? samples[0]

  return (
    <div>
      <div className="pipeline-steps">
        {STEPS.map((step) => (
          <div className="step" key={step.num}>
            <div className="num">{step.num}</div>
            <h4>{step.title}</h4>
            <p>{step.body}</p>
          </div>
        ))}
      </div>

      {meta && (
        <div className="meta-row" style={{ marginBottom: 20 }}>
          <span className="chip">
            <strong>{meta.facts_loaded.toLocaleString()}</strong> facts loaded
          </span>
          <span className="chip">
            <strong>{meta.line_items_tracked}</strong> line items mapped
          </span>
          <span className="chip">
            <strong>{meta.companies}</strong> companies
          </span>
          <span className="chip">
            Built <strong>{new Date(meta.built_at).toLocaleDateString()}</strong>
          </span>
        </div>
      )}

      {current && (
        <div>
          <div className="code-tabs" role="tablist">
            {samples.map((sample) => (
              <button
                key={sample.key}
                role="tab"
                aria-pressed={sample.key === active}
                onClick={() => setActive(sample.key)}
              >
                {sample.label}
              </button>
            ))}
          </div>
          <pre className="code" style={{ maxHeight: 420 }}>
            <code>{current.source}</code>
          </pre>
          <p style={{ fontSize: 12.5, color: 'var(--text-muted)', marginTop: 8 }}>
            {current.caption}
          </p>
        </div>
      )}
    </div>
  )
}

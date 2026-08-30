import { useEffect, useMemo, useState } from 'react'
import type { CompanyData, Meta, PeerData, Year, YearAnalysis } from './types'
import { basisPoints, money, percent } from './format'
import { KpiRow } from './components/KpiRow'
import { CashFlowChart, MarginChart, RevenueChart, ReturnsChart } from './components/Charts'
import { AltmanCard, PiotroskiCard } from './components/Scores'
import { FlagList } from './components/Flags'
import { PeerChart } from './components/Peers'
import { Forecast } from './components/Forecast'
import { HowItWorks, type CodeSample } from './components/HowItWorks'

const SEC_URL = 'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001670592&type=10-K'

/**
 * Find a year where the rule engine flagged inventory building, and report what
 * happened to gross margin the year after.
 *
 * Derived from the data rather than written into the page, so it stays true if
 * the pipeline is re-run with new filings or different thresholds.
 */
function findLeadIndicator(years: Year[], analysis: YearAnalysis[]) {
  for (let i = 0; i < analysis.length - 1; i++) {
    const flag = analysis[i].flags.find((f) => f.key === 'inventory_outpacing_sales')
    if (!flag) continue

    const flaggedYear = years.find((y) => y.fy === analysis[i].fy)
    const nextYear = years.find((y) => y.fy === analysis[i].fy + 1)
    if (!flaggedYear || !nextYear) continue
    if (nextYear.gross_margin === null || flaggedYear.gross_margin === null) continue
    if (nextYear.gross_margin >= flaggedYear.gross_margin) continue

    return { flag, flaggedYear, nextYear }
  }
  return null
}

export default function App() {
  const [company, setCompany] = useState<CompanyData | null>(null)
  const [peers, setPeers] = useState<PeerData | null>(null)
  const [meta, setMeta] = useState<Meta | null>(null)
  const [samples, setSamples] = useState<CodeSample[]>([])
  const [error, setError] = useState<string | null>(null)
  const [selectedFy, setSelectedFy] = useState<number | null>(null)

  useEffect(() => {
    Promise.all([
      fetch('data/company.json').then((r) => r.json()),
      fetch('data/peers.json').then((r) => r.json()),
      fetch('data/meta.json').then((r) => r.json()),
      fetch('data/code.json').then((r) => r.json()),
    ])
      .then(([companyData, peerData, metaData, codeData]) => {
        setCompany(companyData)
        setPeers(peerData)
        setMeta(metaData)
        setSamples(codeData.samples)
        setSelectedFy(companyData.latest_fy)
      })
      .catch(() => setError('Could not load the analysis data.'))
  }, [])

  const leadIndicator = useMemo(
    () => (company ? findLeadIndicator(company.years, company.analysis) : null),
    [company]
  )

  if (error) {
    return (
      <div className="page">
        <p className="empty-state" style={{ marginTop: 60 }}>
          {error} Run <code>python build.py</code> in the pipeline folder to generate it.
        </p>
      </div>
    )
  }

  if (!company || !peers || selectedFy === null) {
    return (
      <div className="page">
        <p style={{ marginTop: 60, color: 'var(--text-muted)' }}>Loading analysis…</p>
      </div>
    )
  }

  const latest = company.years[company.years.length - 1]
  const prior = company.years[company.years.length - 2]
  const selectedAnalysis =
    company.analysis.find((a) => a.fy === selectedFy) ?? company.analysis[company.analysis.length - 1]

  return (
    <div className="page">
      <header className="masthead">
        <p className="eyebrow">Financial statement analysis</p>
        <h1>{company.company.name} ({company.company.ticker})</h1>
        <p className="subtitle">
          Nine years of SEC filings run through a standard metric stack, two published
          health models and a rule engine that looks for divergences worth a second
          look. Every figure traces back to a 10-K.
        </p>
        <div className="meta-row">
          <span className="chip">
            Through <strong>FY{company.latest_fy}</strong>
          </span>
          <span className="chip">
            Revenue <strong>{money(latest.revenue)}</strong>
          </span>
          <span className="chip">
            Source <strong><a href={SEC_URL} target="_blank" rel="noreferrer">SEC EDGAR</a></strong>
          </span>
          <span className="chip">Python · SQL · React</span>
        </div>
      </header>

      {leadIndicator && (
        <section>
          <div className="callout">
            <h3>The check that mattered</h3>
            <p>
              In FY{leadIndicator.flaggedYear.fy} inventory grew{' '}
              {percent(leadIndicator.flaggedYear.inventory_growth)} while revenue grew{' '}
              {percent(leadIndicator.flaggedYear.revenue_growth)}. The rule engine flagged
              the gap as stock building ahead of demand, which typically gets resolved
              through discounting.
            </p>
            <p>
              The following year gross margin fell{' '}
              {basisPoints(
                leadIndicator.nextYear.gross_margin,
                leadIndicator.flaggedYear.gross_margin
              )}
              , from {percent(leadIndicator.flaggedYear.gross_margin)} to{' '}
              {percent(leadIndicator.nextYear.gross_margin)}. The signal sat in the balance
              sheet a full year before it reached the income statement.
            </p>
            <div className="callout-figures">
              <div>
                <span className="value">{percent(leadIndicator.flaggedYear.inventory_growth)}</span>
                <span className="label">FY{leadIndicator.flaggedYear.fy} inventory growth</span>
              </div>
              <div>
                <span className="value">{percent(leadIndicator.flaggedYear.revenue_growth)}</span>
                <span className="label">FY{leadIndicator.flaggedYear.fy} revenue growth</span>
              </div>
              <div>
                <span className="value">
                  {basisPoints(
                    leadIndicator.nextYear.gross_margin,
                    leadIndicator.flaggedYear.gross_margin
                  )}
                </span>
                <span className="label">FY{leadIndicator.nextYear.fy} gross margin</span>
              </div>
            </div>
          </div>
        </section>
      )}

      <section>
        <div className="section-head">
          <h2>FY{latest.fy} at a glance</h2>
          <p>Headline figures against the prior year.</p>
        </div>
        <KpiRow current={latest} prior={prior} />
      </section>

      <section>
        <div className="section-head">
          <h2>Trends</h2>
          <p>
            Nine fiscal years, FY{company.years[0].fy} through FY{company.latest_fy}.
          </p>
        </div>
        <div className="grid-2">
          <RevenueChart years={company.years} />
          <MarginChart years={company.years} />
          <CashFlowChart years={company.years} />
          <ReturnsChart years={company.years} />
        </div>
      </section>

      <section>
        <div className="section-head">
          <h2>Health scores by year</h2>
          <p>
            Two published models. Altman measures distress risk from the balance sheet;
            Piotroski scores nine fundamental tests. Pick a year to see how each was built.
          </p>
        </div>

        <div className="year-picker" role="group" aria-label="Select fiscal year">
          {company.analysis.map((a) => (
            <button
              key={a.fy}
              aria-pressed={a.fy === selectedFy}
              onClick={() => setSelectedFy(a.fy)}
            >
              FY{a.fy}
            </button>
          ))}
        </div>

        <div className="grid-2">
          <AltmanCard altman={selectedAnalysis.altman} />
          <PiotroskiCard piotroski={selectedAnalysis.piotroski} />
        </div>
      </section>

      <section>
        <div className="section-head">
          <h2>Flags raised in FY{selectedAnalysis.fy}</h2>
          <p>
            Ten rules run against every year. Each one names the figures that triggered it
            rather than returning a score.
          </p>
        </div>
        <FlagList flags={selectedAnalysis.flags} fy={selectedAnalysis.fy} />
      </section>

      <section>
        <div className="section-head">
          <h2>Against the peer group</h2>
          <p>
            Percentile within eight apparel and outdoor companies for FY{peers.fy}: Nike,
            Deckers, Lululemon, VF Corp, Columbia, Under Armour, Crocs and {company.company.ticker}.
          </p>
        </div>
        <PeerChart peers={peers} subject={company.company.ticker} />
      </section>

      <section>
        <div className="section-head">
          <h2>Forecast</h2>
          <p>
            A driver-based projection three years out. Move the assumptions and the model
            recomputes, including how much cash the operating cycle absorbs.
          </p>
        </div>
        <Forecast years={company.years} drivers={company.drivers} />
      </section>

      <section>
        <div className="section-head">
          <h2>Written analysis</h2>
          <p>
            Generated from the computed figures above. The model receives the numbers and
            writes the prose; it never does the arithmetic itself.
          </p>
        </div>
        <div className="card memo">
          {company.memo.text.split('\n\n').map((paragraph, i) => (
            <p key={i}>{paragraph}</p>
          ))}
          <div className="memo-source">
            {company.memo.source === 'groq'
              ? `Written by ${company.memo.model} from a structured block of pre-computed facts. Figures were calculated in SQL and Python before the model saw them.`
              : 'Written by the deterministic template. The pipeline falls back to it when no LLM API key is configured, so the page never renders an empty section.'}
          </div>
        </div>
      </section>

      <section>
        <div className="section-head">
          <h2>How this is built</h2>
          <p>
            No server and no database at runtime. The pipeline runs offline and publishes
            static JSON, which is why the page loads instantly and costs nothing to host.
          </p>
        </div>
        <HowItWorks meta={meta} samples={samples} />
      </section>

      <footer>
        <p>
          Built from public filings retrieved from the SEC EDGAR XBRL API. Figures are as
          reported by the company and have not been adjusted for one-time items.
        </p>
        <p>
          The Altman Z''-Score and Piotroski F-Score are published academic models applied
          here to reported figures. They are screening measures, not verdicts, and nothing
          on this page is investment advice.
        </p>
      </footer>
    </div>
  )
}

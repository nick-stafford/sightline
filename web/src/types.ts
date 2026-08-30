// Shapes of the JSON written by the Python pipeline (pipeline/build.py).
// Everything is nullable because a ratio is null whenever its denominator was
// missing or zero in the filing.

export type Num = number | null

export interface Year {
  fy: number
  period_end: string

  revenue: Num
  gross_profit: Num
  ebitda: Num
  ebit: Num
  net_income: Num
  eps_diluted: Num
  operating_cash_flow: Num
  free_cash_flow: Num
  total_assets: Num
  equity: Num
  net_debt: Num
  cash: Num
  inventory: Num
  receivables: Num
  accounts_payable: Num
  long_term_debt: Num
  capex: Num
  depreciation_amortization: Num
  cogs: Num
  current_assets: Num
  current_liabilities: Num

  revenue_growth: Num
  net_income_growth: Num
  gross_profit_growth: Num
  inventory_growth: Num
  receivables_growth: Num
  revenue_cagr_3y: Num
  gross_margin: Num
  ebitda_margin: Num
  operating_margin: Num
  net_margin: Num
  roa: Num
  roe: Num
  roic: Num
  asset_turnover: Num
  equity_multiplier: Num
  net_debt_to_ebitda: Num
  debt_to_equity: Num
  interest_coverage: Num
  current_ratio: Num
  days_inventory: Num
  days_receivables: Num
  days_payables: Num
  cash_conversion_cycle: Num
  fcf_margin: Num
  fcf_conversion: Num
  capex_intensity: Num
  cash_conversion: Num
  accruals_ratio: Num
}

export interface AltmanComponent {
  key: string
  label: string
  value: number
  weight: number
  contribution: number
}

export interface Altman {
  score: number
  zone: 'safe' | 'grey' | 'distress'
  components: AltmanComponent[]
}

export interface PiotroskiSignal {
  key: string
  category: string
  label: string
  passed: boolean
  detail: string
}

export interface Piotroski {
  score: number
  max: number
  band: string
  signals: PiotroskiSignal[]
}

export interface Flag {
  key: string
  severity: 'high' | 'medium' | 'low'
  title: string
  summary: string
  evidence: { label: string; value: string }[]
}

export interface YearAnalysis {
  fy: number
  period_end: string
  altman: Altman | null
  piotroski: Piotroski | null
  flags: Flag[]
}

export interface Drivers {
  base_year: number
  base_revenue: number
  revenue_growth: number
  gross_margin: number
  sga_pct_revenue: number
  capex_intensity: number
  days_inventory: number
  days_receivables: number
  days_payables: number
  da_pct_revenue: number
  tax_rate: number
  opening_cash: number
  opening_debt: number
}

export interface CompanyData {
  company: { ticker: string; name: string; cik: string; brands?: string }
  latest_fy: number
  years: Year[]
  analysis: YearAnalysis[]
  drivers: Drivers
  memo: { text: string; source: 'groq' | 'template'; model: string | null }
}

export interface PeerRank {
  ticker: string
  name: string
  metric: string
  value: number
  percentile: number
  higher_is_better: boolean
}

export interface PeerData {
  fy: number
  cohort: { ticker: string; name: string; brands?: string }[]
  highlights: { key: string; label: string; format: 'percent' | 'multiple' | 'days' }[]
  ranks: PeerRank[]
}

export interface Meta {
  built_at: string
  source: string
  line_items_tracked: number
  facts_loaded: number
  companies: number
  llm: { used: boolean; model: string | null }
  coverage: { ticker: string; fy: number; items: number; missing: string[] }[]
}

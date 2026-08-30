// Driver-based projection.
//
// This runs in the browser rather than in the pipeline because the sliders need
// to recompute on every drag. Keeping it here means there is one implementation
// of the model rather than the same arithmetic in both Python and TypeScript.
//
// It is a simple operating model, not a full three-statement build: revenue
// drives margins, margins drive earnings, and the working capital day counts
// determine how much cash gets tied up along the way. Enough to answer "what
// does this look like if growth stays at 2% and margins hold", which is the
// question the page is asking.

import type { Drivers, Year } from '../types'

export interface DriverInputs {
  revenueGrowth: number
  grossMargin: number
  sgaPctRevenue: number
  capexIntensity: number
  daysInventory: number
  taxRate: number
}

export interface ProjectedYear {
  fy: number
  projected: boolean
  revenue: number
  grossProfit: number
  ebitda: number
  ebit: number
  netIncome: number
  capex: number
  changeInWorkingCapital: number
  freeCashFlow: number
  ebitdaMargin: number
}

export const PROJECTION_YEARS = 3

export function defaultInputs(drivers: Drivers): DriverInputs {
  return {
    revenueGrowth: drivers.revenue_growth ?? 0.03,
    grossMargin: drivers.gross_margin ?? 0.57,
    sgaPctRevenue: drivers.sga_pct_revenue ?? 0.42,
    capexIntensity: drivers.capex_intensity ?? 0.03,
    daysInventory: drivers.days_inventory ?? 120,
    taxRate: drivers.tax_rate ?? 0.24,
  }
}

/**
 * Project forward from the last actual year.
 *
 * Working capital is the part worth reading closely: inventory and receivables
 * are assets, so growing them consumes cash, while payables are a liability and
 * growing them releases it. The projection charges the year-over-year *change*
 * in that net figure against free cash flow, which is why stretching the
 * inventory slider hurts cash long before it touches the income statement.
 */
export function project(
  history: Year[],
  drivers: Drivers,
  inputs: DriverInputs
): ProjectedYear[] {
  const base = history[history.length - 1]

  const daysReceivables = drivers.days_receivables ?? 20
  const daysPayables = drivers.days_payables ?? 45
  const daPctRevenue = drivers.da_pct_revenue ?? 0.03

  // Opening working capital comes from the actual balance sheet, so year one of
  // the projection steps off the real position rather than a modelled one.
  let priorWorkingCapital =
    (base.inventory ?? 0) + (base.receivables ?? 0) - (base.accounts_payable ?? 0)
  let revenue = base.revenue ?? 0

  const rows: ProjectedYear[] = []

  for (let i = 1; i <= PROJECTION_YEARS; i++) {
    revenue = revenue * (1 + inputs.revenueGrowth)

    const grossProfit = revenue * inputs.grossMargin
    const cogs = revenue - grossProfit
    const sga = revenue * inputs.sgaPctRevenue

    const ebitda = grossProfit - sga
    const da = revenue * daPctRevenue
    const ebit = ebitda - da

    // YETI carries almost no debt, so the model doesn't try to schedule
    // interest. If this were applied to a levered business that assumption
    // would need replacing.
    const pretax = ebit
    const tax = Math.max(pretax, 0) * inputs.taxRate
    const netIncome = pretax - tax

    const capex = revenue * inputs.capexIntensity

    const inventory = (inputs.daysInventory * cogs) / 365
    const receivables = (daysReceivables * revenue) / 365
    const payables = (daysPayables * cogs) / 365
    const workingCapital = inventory + receivables - payables
    const changeInWorkingCapital = workingCapital - priorWorkingCapital
    priorWorkingCapital = workingCapital

    const freeCashFlow = netIncome + da - capex - changeInWorkingCapital

    rows.push({
      fy: (base.fy ?? drivers.base_year) + i,
      projected: true,
      revenue,
      grossProfit,
      ebitda,
      ebit,
      netIncome,
      capex,
      changeInWorkingCapital,
      freeCashFlow,
      ebitdaMargin: ebitda / revenue,
    })
  }

  return rows
}

/** Historical years in the same shape, so the chart can plot one continuous line. */
export function historyAsProjection(history: Year[]): ProjectedYear[] {
  return history.map((year) => ({
    fy: year.fy,
    projected: false,
    revenue: year.revenue ?? 0,
    grossProfit: year.gross_profit ?? 0,
    ebitda: year.ebitda ?? 0,
    ebit: year.ebit ?? 0,
    netIncome: year.net_income ?? 0,
    capex: year.capex ?? 0,
    changeInWorkingCapital: 0,
    freeCashFlow: year.free_cash_flow ?? 0,
    ebitdaMargin: year.ebitda_margin ?? 0,
  }))
}

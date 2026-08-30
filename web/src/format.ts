// Number formatting. Everything arriving from the pipeline can be null, so each
// helper takes Num and returns an em dash rather than "NaN" or "null".

import type { Num } from './types'

const DASH = '—'

export function money(value: Num, digits = 0): string {
  if (value === null || value === undefined) return DASH
  const abs = Math.abs(value)
  if (abs >= 1e9) return `$${(value / 1e9).toFixed(2)}B`
  if (abs >= 1e6) return `$${(value / 1e6).toFixed(digits)}M`
  return `$${value.toLocaleString('en-US', { maximumFractionDigits: 0 })}`
}

export function percent(value: Num, digits = 1): string {
  if (value === null || value === undefined) return DASH
  return `${(value * 100).toFixed(digits)}%`
}

export function multiple(value: Num, digits = 2): string {
  if (value === null || value === undefined) return DASH
  return `${value.toFixed(digits)}x`
}

export function days(value: Num): string {
  if (value === null || value === undefined) return DASH
  return `${Math.round(value)} days`
}

export function basisPoints(current: Num, prior: Num): string {
  if (current === null || prior === null) return DASH
  const bps = Math.round((current - prior) * 10000)
  return `${bps >= 0 ? '+' : ''}${bps} bps`
}

/** Signed change for a stat tile, formatted in the units of the metric. */
export function delta(current: Num, prior: Num, kind: 'percent' | 'multiple' | 'money' | 'days'): string {
  if (current === null || prior === null) return DASH
  const diff = current - prior
  const sign = diff >= 0 ? '+' : ''
  switch (kind) {
    case 'percent':
      return `${sign}${(diff * 100).toFixed(1)} pts`
    case 'multiple':
      return `${sign}${diff.toFixed(2)}x`
    case 'days':
      return `${sign}${Math.round(diff)} days`
    case 'money':
      return `${sign}${money(diff)}`
  }
}

export function fiscalLabel(fy: number): string {
  return `FY${String(fy).slice(2)}`
}

/** Format a value using the display kind the pipeline tagged it with. */
export function byFormat(value: Num, format: 'percent' | 'multiple' | 'days'): string {
  if (format === 'percent') return percent(value)
  if (format === 'days') return days(value)
  return multiple(value)
}

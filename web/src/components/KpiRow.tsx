import type { Num, Year } from '../types'
import { delta, money, multiple, percent } from '../format'

interface Props {
  current: Year
  prior: Year | undefined
}

type Kind = 'money' | 'percent' | 'multiple'

interface Tile {
  label: string
  value: string
  change: string
  /** Whether an increase in this metric is a good thing. Net leverage is not. */
  higherIsBetter: boolean
  raw: Num
  priorRaw: Num
}

export function KpiRow({ current, prior }: Props) {
  const tile = (
    label: string,
    key: keyof Year,
    kind: Kind,
    higherIsBetter = true
  ): Tile => {
    const raw = current[key] as Num
    const priorRaw = (prior?.[key] ?? null) as Num
    const value =
      kind === 'money' ? money(raw) : kind === 'percent' ? percent(raw) : multiple(raw)
    return {
      label,
      value,
      change: delta(raw, priorRaw, kind),
      higherIsBetter,
      raw,
      priorRaw,
    }
  }

  const tiles: Tile[] = [
    tile('Revenue', 'revenue', 'money'),
    tile('EBITDA margin', 'ebitda_margin', 'percent'),
    tile('ROIC', 'roic', 'percent'),
    tile('Net debt / EBITDA', 'net_debt_to_ebitda', 'multiple', false),
    tile('FCF conversion', 'fcf_conversion', 'percent'),
  ]

  return (
    <div className="kpi-row">
      {tiles.map((t) => {
        let direction = ''
        if (t.raw !== null && t.priorRaw !== null) {
          const improved = t.higherIsBetter ? t.raw > t.priorRaw : t.raw < t.priorRaw
          direction = improved ? 'up' : 'down'
        }
        return (
          <div className="kpi" key={t.label}>
            <div className="label">{t.label}</div>
            <div className="value">{t.value}</div>
            <div className={`change ${direction}`}>{t.change} vs prior year</div>
          </div>
        )
      })}
    </div>
  )
}

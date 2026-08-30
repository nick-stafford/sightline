import { useMemo, useState } from 'react'
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { TooltipProps } from 'recharts'
import type { Drivers, Year } from '../types'
import {
  PROJECTION_YEARS,
  defaultInputs,
  historyAsProjection,
  project,
  type DriverInputs,
} from '../lib/projection'
import { fiscalLabel, money, percent } from '../format'

interface Props {
  years: Year[]
  drivers: Drivers
}

interface SliderSpec {
  key: keyof DriverInputs
  label: string
  min: number
  max: number
  step: number
  format: (value: number) => string
  hint: string
}

const SLIDERS: SliderSpec[] = [
  {
    key: 'revenueGrowth',
    label: 'Revenue growth',
    min: -0.1,
    max: 0.25,
    step: 0.005,
    format: (v) => `${(v * 100).toFixed(1)}%`,
    hint: 'Applied to every projected year',
  },
  {
    key: 'grossMargin',
    label: 'Gross margin',
    min: 0.4,
    max: 0.65,
    step: 0.005,
    format: (v) => `${(v * 100).toFixed(1)}%`,
    hint: 'Fell to 47.9% in the FY22 recall year',
  },
  {
    key: 'sgaPctRevenue',
    label: 'SG&A % of revenue',
    min: 0.3,
    max: 0.55,
    step: 0.005,
    format: (v) => `${(v * 100).toFixed(1)}%`,
    hint: 'Operating cost base',
  },
  {
    key: 'capexIntensity',
    label: 'Capex % of revenue',
    min: 0,
    max: 0.1,
    step: 0.0025,
    format: (v) => `${(v * 100).toFixed(2)}%`,
    hint: 'Reinvestment rate',
  },
  {
    key: 'daysInventory',
    label: 'Days inventory',
    min: 60,
    max: 220,
    step: 1,
    format: (v) => `${Math.round(v)} days`,
    hint: 'Higher ties up more cash',
  },
  {
    key: 'taxRate',
    label: 'Tax rate',
    min: 0.15,
    max: 0.35,
    step: 0.005,
    format: (v) => `${(v * 100).toFixed(1)}%`,
    hint: 'Effective rate',
  },
]

function ForecastTooltip({ active, payload, label }: TooltipProps<number, string>) {
  if (!active || !payload?.length) return null
  const point = payload[0].payload as { revenue: number; ebitda: number; projected: boolean }
  return (
    <div className="tooltip">
      <div className="tooltip-title">
        {label} {point.projected ? '(projected)' : '(actual)'}
      </div>
      <div className="tooltip-row">
        <span className="swatch" style={{ background: 'var(--series-1)' }} />
        <span>Revenue</span>
        <span className="num">{money(point.revenue * 1e6)}</span>
      </div>
      <div className="tooltip-row">
        <span className="swatch" style={{ background: 'var(--series-2)' }} />
        <span>EBITDA</span>
        <span className="num">{money(point.ebitda * 1e6)}</span>
      </div>
    </div>
  )
}

export function Forecast({ years, drivers }: Props) {
  const [inputs, setInputs] = useState<DriverInputs>(() => defaultInputs(drivers))

  const projected = useMemo(() => project(years, drivers, inputs), [years, drivers, inputs])
  const history = useMemo(() => historyAsProjection(years), [years])

  // One continuous series for actuals and a second that starts at the last
  // actual point, so the projected line joins on rather than floating.
  const chartData = useMemo(() => {
    const all = [...history, ...projected]
    const lastActualIndex = history.length - 1
    return all.map((row, i) => ({
      label: fiscalLabel(row.fy),
      projected: row.projected,
      revenue: row.revenue / 1e6,
      ebitda: row.ebitda / 1e6,
      actualRevenue: i <= lastActualIndex ? row.revenue / 1e6 : null,
      projectedRevenue: i >= lastActualIndex ? row.revenue / 1e6 : null,
    }))
  }, [history, projected])

  const isDefault = SLIDERS.every(
    (s) => Math.abs(inputs[s.key] - defaultInputs(drivers)[s.key]) < 1e-9
  )

  return (
    <div className="forecast-layout">
      <div className="card">
        <h3 style={{ margin: '0 0 4px', fontSize: 15 }}>Drivers</h3>
        <p style={{ margin: '0 0 16px', fontSize: 12.5, color: 'var(--text-muted)' }}>
          Defaults are the company's own three-year averages.
        </p>

        {SLIDERS.map((slider) => (
          <div className="driver" key={slider.key}>
            <div className="driver-head">
              <label className="name" htmlFor={slider.key}>
                {slider.label}
              </label>
              <span className="val">{slider.format(inputs[slider.key])}</span>
            </div>
            <input
              id={slider.key}
              type="range"
              min={slider.min}
              max={slider.max}
              step={slider.step}
              value={inputs[slider.key]}
              onChange={(e) =>
                setInputs((prev) => ({ ...prev, [slider.key]: Number(e.target.value) }))
              }
            />
            <div className="hint">{slider.hint}</div>
          </div>
        ))}

        <button
          className="reset-btn"
          onClick={() => setInputs(defaultInputs(drivers))}
          disabled={isDefault}
        >
          Reset to historical averages
        </button>
      </div>

      <div>
        <div className="chart-card">
          <h3>Revenue, actual and projected</h3>
          <p className="note">
            US$ millions. The dashed segment is the {PROJECTION_YEARS}-year projection
            from the drivers on the left.
          </p>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={chartData} margin={{ top: 8, right: 8, bottom: 4, left: 4 }}>
              <CartesianGrid stroke="var(--grid)" vertical={false} />
              <XAxis
                dataKey="label"
                tick={{ fill: 'var(--text-muted)', fontSize: 12 }}
                tickLine={false}
                axisLine={{ stroke: 'var(--axis)' }}
              />
              <YAxis
                tick={{ fill: 'var(--text-muted)', fontSize: 12 }}
                tickLine={false}
                axisLine={false}
                width={50}
              />
              <Tooltip content={<ForecastTooltip />} cursor={{ stroke: 'var(--axis)' }} />
              <Line
                type="monotone"
                dataKey="actualRevenue"
                name="Actual"
                stroke="var(--series-1)"
                strokeWidth={2}
                dot={{ r: 4, strokeWidth: 0, fill: 'var(--series-1)' }}
                connectNulls
              />
              <Line
                type="monotone"
                dataKey="projectedRevenue"
                name="Projected"
                stroke="var(--series-1)"
                strokeWidth={2}
                strokeDasharray="5 4"
                dot={{ r: 4, strokeWidth: 0, fill: 'var(--series-1)' }}
                connectNulls
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <table className="projection-table">
          <thead>
            <tr>
              <th>Fiscal year</th>
              <th>Revenue</th>
              <th>EBITDA</th>
              <th>EBITDA margin</th>
              <th>Working capital</th>
              <th>Free cash flow</th>
            </tr>
          </thead>
          <tbody>
            {projected.map((row) => (
              <tr className="projected" key={row.fy}>
                <td>FY{String(row.fy).slice(2)}E</td>
                <td>{money(row.revenue)}</td>
                <td>{money(row.ebitda)}</td>
                <td>{percent(row.ebitdaMargin)}</td>
                <td>{money(-row.changeInWorkingCapital)}</td>
                <td>{money(row.freeCashFlow)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p style={{ fontSize: 12.5, color: 'var(--text-muted)', marginTop: 10 }}>
          Working capital shows the cash effect: negative means the operating cycle
          absorbed cash that year.
        </p>
      </div>
    </div>
  )
}

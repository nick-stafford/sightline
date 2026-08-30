import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { TooltipProps } from 'recharts'
import type { Year } from '../types'
import { fiscalLabel, money, percent } from '../format'

// Colors come through as CSS custom properties rather than hex so the charts
// follow the light/dark tokens without a second palette in JS.
const SERIES = {
  one: 'var(--series-1)',
  two: 'var(--series-2)',
  three: 'var(--series-3)',
}

const axisStyle = { fill: 'var(--text-muted)', fontSize: 12 }

interface Formatted {
  [key: string]: string
}

/** One tooltip for every chart. Values are pre-formatted by the caller. */
function ChartTooltip({ active, payload, label }: TooltipProps<number, string>) {
  if (!active || !payload?.length) return null
  return (
    <div className="tooltip">
      <div className="tooltip-title">{label}</div>
      {payload.map((entry) => {
        const formatted = (entry.payload as { formatted?: Formatted }).formatted
        const shown = formatted?.[entry.dataKey as string] ?? String(entry.value)
        return (
          <div className="tooltip-row" key={entry.dataKey as string}>
            <span className="swatch" style={{ background: entry.color }} />
            <span>{entry.name}</span>
            <span className="num">{shown}</span>
          </div>
        )
      })}
    </div>
  )
}

interface ChartProps {
  years: Year[]
}

export function RevenueChart({ years }: ChartProps) {
  const data = years.map((y) => ({
    label: fiscalLabel(y.fy),
    revenue: (y.revenue ?? 0) / 1e6,
    formatted: {
      revenue: `${money(y.revenue)}  (${percent(y.revenue_growth)} YoY)`,
    },
  }))

  return (
    <div className="chart-card">
      <h3>Revenue</h3>
      <p className="note">US$ millions. Hover for year-over-year growth.</p>
      <ResponsiveContainer width="100%" height={230}>
        <BarChart data={data} margin={{ top: 8, right: 8, bottom: 4, left: 4 }}>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis dataKey="label" tick={axisStyle} tickLine={false} axisLine={{ stroke: 'var(--axis)' }} />
          <YAxis
            tick={axisStyle}
            tickLine={false}
            axisLine={false}
            width={46}
            tickFormatter={(v: number) => `${v.toLocaleString()}`}
          />
          <Tooltip content={<ChartTooltip />} cursor={{ fill: 'var(--grid)', opacity: 0.4 }} />
          <Bar dataKey="revenue" name="Revenue" fill={SERIES.one} radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

export function MarginChart({ years }: ChartProps) {
  const data = years.map((y) => ({
    label: fiscalLabel(y.fy),
    gross: y.gross_margin === null ? null : y.gross_margin * 100,
    ebitda: y.ebitda_margin === null ? null : y.ebitda_margin * 100,
    net: y.net_margin === null ? null : y.net_margin * 100,
    formatted: {
      gross: percent(y.gross_margin),
      ebitda: percent(y.ebitda_margin),
      net: percent(y.net_margin),
    },
  }))

  return (
    <div className="chart-card">
      <h3>Margins</h3>
      <p className="note">
        The FY22 step down is the product recall and inventory markdown year.
      </p>
      <ResponsiveContainer width="100%" height={230}>
        <LineChart data={data} margin={{ top: 8, right: 8, bottom: 4, left: 4 }}>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis dataKey="label" tick={axisStyle} tickLine={false} axisLine={{ stroke: 'var(--axis)' }} />
          <YAxis
            tick={axisStyle}
            tickLine={false}
            axisLine={false}
            width={46}
            tickFormatter={(v: number) => `${v}%`}
          />
          <Tooltip content={<ChartTooltip />} cursor={{ stroke: 'var(--axis)', strokeWidth: 1 }} />
          <Legend
            iconType="circle"
            iconSize={9}
            wrapperStyle={{ fontSize: 12.5, color: 'var(--text-secondary)', paddingTop: 6 }}
          />
          <Line
            type="monotone"
            dataKey="gross"
            name="Gross margin"
            stroke={SERIES.one}
            strokeWidth={2}
            dot={{ r: 4, strokeWidth: 0, fill: SERIES.one }}
            activeDot={{ r: 5 }}
            connectNulls
          />
          <Line
            type="monotone"
            dataKey="ebitda"
            name="EBITDA margin"
            stroke={SERIES.two}
            strokeWidth={2}
            dot={{ r: 4, strokeWidth: 0, fill: SERIES.two }}
            activeDot={{ r: 5 }}
            connectNulls
          />
          <Line
            type="monotone"
            dataKey="net"
            name="Net margin"
            stroke={SERIES.three}
            strokeWidth={2}
            dot={{ r: 4, strokeWidth: 0, fill: SERIES.three }}
            activeDot={{ r: 5 }}
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

export function CashFlowChart({ years }: ChartProps) {
  const data = years.map((y) => ({
    label: fiscalLabel(y.fy),
    fcf: (y.free_cash_flow ?? 0) / 1e6,
    formatted: {
      fcf: `${money(y.free_cash_flow)}  (${percent(y.fcf_conversion)} of EBITDA)`,
    },
  }))

  return (
    <div className="chart-card">
      <h3>Free cash flow</h3>
      <p className="note">
        US$ millions, after capital spending. Hover for conversion from EBITDA.
      </p>
      <ResponsiveContainer width="100%" height={230}>
        <BarChart data={data} margin={{ top: 8, right: 8, bottom: 4, left: 4 }}>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis dataKey="label" tick={axisStyle} tickLine={false} axisLine={{ stroke: 'var(--axis)' }} />
          <YAxis tick={axisStyle} tickLine={false} axisLine={false} width={46} />
          <Tooltip content={<ChartTooltip />} cursor={{ fill: 'var(--grid)', opacity: 0.4 }} />
          <Bar dataKey="fcf" name="Free cash flow" fill={SERIES.three} radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

export function ReturnsChart({ years }: ChartProps) {
  const data = years.map((y) => ({
    label: fiscalLabel(y.fy),
    roic: y.roic === null ? null : y.roic * 100,
    formatted: { roic: percent(y.roic) },
  }))

  return (
    <div className="chart-card">
      <h3>Return on invested capital</h3>
      <p className="note">
        NOPAT over capital employed. The single measure least distorted by how the
        business is financed.
      </p>
      <ResponsiveContainer width="100%" height={230}>
        <LineChart data={data} margin={{ top: 8, right: 8, bottom: 4, left: 4 }}>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis dataKey="label" tick={axisStyle} tickLine={false} axisLine={{ stroke: 'var(--axis)' }} />
          <YAxis
            tick={axisStyle}
            tickLine={false}
            axisLine={false}
            width={46}
            tickFormatter={(v: number) => `${v}%`}
          />
          <Tooltip content={<ChartTooltip />} cursor={{ stroke: 'var(--axis)', strokeWidth: 1 }} />
          <Line
            type="monotone"
            dataKey="roic"
            name="ROIC"
            stroke={SERIES.one}
            strokeWidth={2}
            dot={{ r: 4, strokeWidth: 0, fill: SERIES.one }}
            activeDot={{ r: 5 }}
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

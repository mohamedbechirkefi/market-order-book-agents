// SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0
// Hand-written SVG and HTML charts. Every chart has a plain-language description and a
// table or printed values beside it; uncertainty is drawn, never left to a tooltip.
import type { BookSnapshot } from "./engine/sim";

// ------------------------------------------------------------------ interval (forest) plot

export interface IntervalRow {
  key: string;
  label: string;
  note?: string;
  estimate: number;
  lo: number;
  hi: number;
  display: string;
  interval_display: string;
}

function niceTicks(lo: number, hi: number, n = 4): number[] {
  const span = hi - lo;
  const step0 = span / n;
  const mag = 10 ** Math.floor(Math.log10(step0));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => span / s <= n) ?? 10 * mag;
  const out: number[] = [];
  for (let v = Math.ceil(lo / step) * step; v <= hi + 1e-12; v += step) out.push(Number(v.toPrecision(10)));
  return out;
}

const tickText = (v: number) => (v === 0 ? "0" : Number(v.toPrecision(3)).toString());

export function IntervalPlot({ rows, axisLabel, id }: { rows: IntervalRow[]; axisLabel: string; id: string }) {
  let lo = Math.min(0, ...rows.map((r) => r.lo));
  let hi = Math.max(0, ...rows.map((r) => r.hi));
  const pad = (hi - lo) * 0.06;
  lo -= pad;
  hi += pad;
  const x = (v: number) => ((v - lo) / (hi - lo)) * 100;
  const ticks = niceTicks(lo, hi);
  return (
    <div className="iplot" role="group" aria-labelledby={`${id}-cap`}>
      {rows.map((r) => (
        <div className="iplot-row" key={r.key}>
          <div className="iplot-label">
            <span>{r.label}</span>
            {r.note && <span className="iplot-note">{r.note}</span>}
          </div>
          <svg className="iplot-svg" viewBox="0 0 100 24" preserveAspectRatio="none" aria-hidden="true" focusable="false">
            <line x1={x(0)} x2={x(0)} y1={0} y2={24} className="zero" vectorEffect="non-scaling-stroke" />
            <line x1={x(r.lo)} x2={x(r.hi)} y1={12} y2={12} className="ci" vectorEffect="non-scaling-stroke" />
            <line x1={x(r.lo)} x2={x(r.lo)} y1={7} y2={17} className="ci" vectorEffect="non-scaling-stroke" />
            <line x1={x(r.hi)} x2={x(r.hi)} y1={7} y2={17} className="ci" vectorEffect="non-scaling-stroke" />
            <line x1={x(r.estimate)} x2={x(r.estimate)} y1={3} y2={21} className="est" vectorEffect="non-scaling-stroke" />
          </svg>
          <div className="iplot-num">
            <span className="mono">{r.display}</span> <span className="mono muted">{r.interval_display}</span>
          </div>
        </div>
      ))}
      <div className="iplot-row iplot-axis" aria-hidden="true">
        <div className="iplot-label" />
        <div className="iplot-ticks">
          {ticks.map((t) => (
            <span key={t} style={{ left: `${x(t)}%` }}>
              {tickText(t)}
            </span>
          ))}
        </div>
        <div className="iplot-num muted">{axisLabel}</div>
      </div>
    </div>
  );
}

// ------------------------------------------------------------------ price paths

export interface Path {
  key: string;
  title: string;
  every: number;
  mid: number[];
}

export function PricePanel({
  path,
  yDomain,
  burnIn,
  marker,
  shockStep,
}: {
  path: Path;
  yDomain: [number, number];
  burnIn: number;
  marker?: number | null;
  shockStep?: number | null;
}) {
  const W = 320;
  const H = 150;
  const L = 40;
  const R = 8;
  const T = 8;
  const B = 24;
  const steps = (path.mid.length - 1) * path.every;
  const [y0, y1] = yDomain;
  const sx = (s: number) => L + (s / steps) * (W - L - R);
  const sy = (v: number) => T + (1 - (v - y0) / (y1 - y0)) * (H - T - B);
  const d = path.mid.map((v, i) => `${i ? "L" : "M"}${sx(i * path.every).toFixed(2)},${sy(v).toFixed(2)}`).join("");
  const yt = niceTicks(y0, y1, 3);
  const xt = [0, steps / 2, steps];
  return (
    <svg className="price" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`${path.title}: mid price from ${path.mid[0]} to ${path.mid[path.mid.length - 1]} price units over ${steps.toLocaleString("en")} steps`}>
      <rect x={sx(0)} y={T} width={sx(Math.min(burnIn, steps)) - sx(0)} height={H - T - B} className="burn" />
      {yt.map((v) => (
        <g key={v}>
          <line x1={L} x2={W - R} y1={sy(v)} y2={sy(v)} className="grid" />
          <text x={L - 4} y={sy(v) + 3} textAnchor="end" className="axis">
            {tickText(v)}
          </text>
        </g>
      ))}
      {xt.map((s) => (
        <text key={s} x={sx(s)} y={H - 8} textAnchor={s === 0 ? "start" : s === steps ? "end" : "middle"} className="axis">
          {s === 0 ? "0" : `${s / 1000}k`}
        </text>
      ))}
      {shockStep != null && <line x1={sx(shockStep)} x2={sx(shockStep)} y1={T} y2={H - B} className="shock" />}
      <path d={d} className="mid" />
      {marker != null && <line x1={sx(marker)} x2={sx(marker)} y1={T} y2={H - B} className="marker" />}
    </svg>
  );
}

export function domainOf(paths: { mid: number[] }[]): [number, number] {
  let lo = Infinity;
  let hi = -Infinity;
  for (const p of paths) for (const v of p.mid) {
    if (v < lo) lo = v;
    if (v > hi) hi = v;
  }
  const pad = Math.max(1, (hi - lo) * 0.05);
  return [lo - pad, hi + pad];
}

// ------------------------------------------------------------------ order book ladder

export function BookLadder({ snap, caption }: { snap: BookSnapshot; caption: string }) {
  const asks = [...snap.asks].reverse();
  const max = Math.max(1, ...snap.asks.map((a) => a[1]), ...snap.bids.map((b) => b[1]));
  const bb = snap.bids[0]?.[0];
  const ba = snap.asks[0]?.[0];
  return (
    <table className="ladder">
      <caption>{caption}</caption>
      <thead>
        <tr>
          <th scope="col">Side</th>
          <th scope="col">Price</th>
          <th scope="col">Resting units</th>
        </tr>
      </thead>
      <tbody>
        {asks.length === 0 && (
          <tr>
            <td>Ask</td>
            <td colSpan={2}>no resting sell orders</td>
          </tr>
        )}
        {asks.map(([p, q]) => (
          <tr key={`a${p}`} className="ask">
            <td>Ask</td>
            <td className="mono">{p}</td>
            <td>
              <div className="units">
                <span className="mono qty">{q}</span>
                <span className="bar" style={{ width: `${(q / max) * 78}%` }} aria-hidden="true" />
              </div>
            </td>
          </tr>
        ))}
        <tr className="spread-row">
          <td colSpan={3}>{bb !== undefined && ba !== undefined ? `spread ${ba - bb} price units` : "one side of the book is empty"}</td>
        </tr>
        {snap.bids.map(([p, q]) => (
          <tr key={`b${p}`} className="bid">
            <td>Bid</td>
            <td className="mono">{p}</td>
            <td>
              <div className="units">
                <span className="mono qty">{q}</span>
                <span className="bar" style={{ width: `${(q / max) * 78}%` }} aria-hidden="true" />
              </div>
            </td>
          </tr>
        ))}
        {snap.bids.length === 0 && (
          <tr>
            <td>Bid</td>
            <td colSpan={2}>no resting buy orders</td>
          </tr>
        )}
      </tbody>
    </table>
  );
}

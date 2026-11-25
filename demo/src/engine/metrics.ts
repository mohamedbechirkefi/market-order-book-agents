// SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0
// Port of the per-run metrics in src/market/metrics.py that the sandbox shows.
// Undefined values are null, never 0. Floating-point sums run in a different order from
// numpy's, so these agree with the Python values within a stated tolerance, not bit for bit.
import type { SimOutput } from "./sim";

export const VCI_MAX_LAG = 10;

export function sampledLogReturns(mid: Float64Array, burnIn: number, dt: number): number[] {
  const r: number[] = [];
  let prev = mid[burnIn];
  for (let i = burnIn + dt; i < mid.length; i += dt) {
    const m = mid[i];
    if (!(m > 0) || !(prev > 0)) throw new Error("mid prices must be finite and positive");
    r.push(Math.log(m) - Math.log(prev));
    prev = m;
  }
  return r;
}

const mean = (x: number[]): number => x.reduce((a, b) => a + b, 0) / x.length;

export function acf(x: number[], lag: number): number | null {
  if (x.length < lag + 2) return null;
  const xb = mean(x);
  const d = x.map((v) => v - xb);
  let den = 0;
  for (const v of d) den += v * v;
  if (den <= 0) return null;
  let num = 0;
  for (let i = 0; i + lag < d.length; i++) num += d[i] * d[i + lag];
  return num / den;
}

export function vci(r: number[], maxLag = VCI_MAX_LAG): number | null {
  const a = r.map(Math.abs);
  let s = 0;
  for (let l = 1; l <= maxLag; l++) {
    const v = acf(a, l);
    if (v === null) return null;
    s += v;
  }
  return s / maxLag;
}

export function sd(x: number[]): number | null {
  if (x.length < 2) return null;
  const m = mean(x);
  let s = 0;
  for (const v of x) s += (v - m) * (v - m);
  return Math.sqrt(s / (x.length - 1));
}

export function maxDrawdown(m: ArrayLike<number>, from = 0): number {
  let peak = -Infinity;
  let dd = 0;
  for (let i = from; i < m.length; i++) {
    if (m[i] > peak) peak = m[i];
    const v = 1 - m[i] / peak;
    if (v > dd) dd = v;
  }
  return dd;
}

export interface RunMetrics {
  vci: number | null;
  realised_volatility: number | null;
  return_acf1: number | null;
  mean_spread: number | null;
  mean_depth_at_best: number | null;
  volume_per_step: number;
  max_drawdown: number;
  one_sided_fraction: number;
  n_returns: number;
  n_nonzero_returns: number;
  final_mid: number;
  degenerate: boolean;
}

export function computeMetrics(out: SimOutput): RunMetrics {
  const B = out.config.burn_in;
  const dt = out.config.sample_interval;
  const r = sampledLogReturns(out.mid, B, dt);
  let two = 0;
  let spreadSum = 0;
  let depthSum = 0;
  let vol = 0;
  const nPost = out.mid.length - (B + 1);
  for (let t = B + 1; t < out.mid.length; t++) {
    vol += out.volume[t];
    if (out.best_bid[t] > 0 && out.best_ask[t] > 0) {
      two++;
      spreadSum += out.best_ask[t] - out.best_bid[t];
      depthSum += out.depth_best[t];
    }
  }
  const nonzero = r.filter((x) => x !== 0).length;
  const oneSided = 1 - two / nPost;
  return {
    vci: vci(r),
    realised_volatility: sd(r),
    return_acf1: acf(r, 1),
    mean_spread: two ? spreadSum / two : null,
    mean_depth_at_best: two ? depthSum / two : null,
    volume_per_step: vol / nPost,
    max_drawdown: maxDrawdown(out.mid, B),
    one_sided_fraction: oneSided,
    n_returns: r.length,
    n_nonzero_returns: nonzero,
    final_mid: out.mid[out.mid.length - 1],
    degenerate: oneSided > 0.05 || nonzero < 50,
  };
}

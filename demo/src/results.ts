// SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0
// Published results: loaded from public/data/results.json, which
// scripts/export_demo_data.py writes from committed results only.
// Validation fails closed: any missing or malformed field means no numbers are shown.

export const SCHEMA = "lab-demo-results";
export const SCHEMA_MAJOR = 1;

export interface Estimate {
  label: string;
  estimate: number;
  ci_low: number | null;
  ci_high: number | null;
  ci_level: number | null;
  unit: string;
  /** Exact text the manuscript prints for the estimate and interval; shown verbatim when present. */
  display: string | null;
  interval_display: string | null;
}

export interface Experiment {
  id: string;
  title: string;
  status: string;
  verdict: string;
  estimates: Estimate[];
  claim_ids: string[];
  report_path: string;
  notes: string[];
}

export interface Assumption {
  name: string;
  value: string;
  source: string;
}

export interface Source {
  path: string;
  sha256: string;
}

export interface Results {
  schema: string;
  schema_version: string;
  project: string;
  question: string;
  status_label: string;
  code_revision: string;
  sources: Source[];
  experiments: Experiment[];
  assumptions: Assumption[];
  limitations: string[];
}

/** MARKET extensions (additional top-level keys, validated fail-closed like the rest). */
export interface Headline {
  frozen_verdict: string;
  frozen_text: string;
  secondary_reading: string;
  secondary_text: string;
}

export interface NotMeasured {
  exp_id: string;
  outcome: string;
  status: string;
  reason: string;
}

export interface DtGrid {
  label: string;
  source: string;
  claim_ids: string[];
  unit: string;
  contrasts: string[];
  rows: { dt: number; cells: Estimate[] }[];
}

export interface MidPath {
  arm: string;
  label: string;
  run_id: string;
  every: number;
  mid: number[];
}

export interface MidPaths {
  label: string;
  unit: string;
  source: string;
  burn_in: number;
  arms: MidPath[];
}

export interface MarketResults extends Results {
  headline: Headline;
  not_measured: NotMeasured[];
  exploratory_dt_grid: DtGrid;
  mid_paths: MidPaths;
}

export class ResultsError extends Error {}

type Obj = Record<string, unknown>;

function obj(v: unknown, where: string): Obj {
  if (typeof v !== "object" || v === null || Array.isArray(v)) {
    throw new ResultsError(`${where}: expected an object`);
  }
  return v as Obj;
}

function str(o: Obj, k: string, where: string): string {
  const v = o[k];
  if (typeof v !== "string" || v.length === 0) {
    throw new ResultsError(`${where}.${k}: expected a non-empty string`);
  }
  return v;
}

function num(o: Obj, k: string, where: string, nullable = false): number | null {
  const v = o[k];
  if (nullable && v === null) return null;
  if (typeof v !== "number" || !Number.isFinite(v)) {
    throw new ResultsError(`${where}.${k}: expected a finite number`);
  }
  return v;
}

function arr(o: Obj, k: string, where: string): unknown[] {
  const v = o[k];
  if (!Array.isArray(v)) throw new ResultsError(`${where}.${k}: expected an array`);
  return v;
}

function strArr(o: Obj, k: string, where: string): string[] {
  return arr(o, k, where).map((v, i) => {
    if (typeof v !== "string") throw new ResultsError(`${where}.${k}[${i}]: expected a string`);
    return v;
  });
}

function estimate(v: unknown, where: string): Estimate {
  const o = obj(v, where);
  const e: Estimate = {
    label: str(o, "label", where),
    estimate: num(o, "estimate", where) as number,
    ci_low: num(o, "ci_low", where, true),
    ci_high: num(o, "ci_high", where, true),
    ci_level: num(o, "ci_level", where, true),
    unit: typeof o.unit === "string" ? o.unit : "",
    display: typeof o.display === "string" ? o.display : null,
    interval_display: typeof o.interval_display === "string" ? o.interval_display : null,
  };
  if ((e.ci_low === null) !== (e.ci_high === null)) {
    throw new ResultsError(`${where}: interval must have both bounds or neither`);
  }
  if (e.ci_low !== null && e.ci_high !== null && e.ci_low > e.ci_high) {
    throw new ResultsError(`${where}: ci_low exceeds ci_high`);
  }
  return e;
}

export function validateCore(raw: unknown): Results {
  const o = obj(raw, "results");
  if (o.schema !== SCHEMA) throw new ResultsError(`results.schema: expected "${SCHEMA}"`);
  const version = str(o, "schema_version", "results");
  if (Number(version.split(".")[0]) !== SCHEMA_MAJOR) {
    throw new ResultsError(`results.schema_version: unsupported major version ${version}`);
  }
  const experiments = arr(o, "experiments", "results").map((v, i) => {
    const w = `experiments[${i}]`;
    const e = obj(v, w);
    return {
      id: str(e, "id", w),
      title: str(e, "title", w),
      status: str(e, "status", w),
      verdict: str(e, "verdict", w),
      estimates: arr(e, "estimates", w).map((x, j) => estimate(x, `${w}.estimates[${j}]`)),
      claim_ids: strArr(e, "claim_ids", w),
      report_path: str(e, "report_path", w),
      notes: strArr(e, "notes", w),
    };
  });
  if (experiments.length === 0) throw new ResultsError("results.experiments: empty");
  return {
    schema: SCHEMA,
    schema_version: version,
    project: str(o, "project", "results"),
    question: str(o, "question", "results"),
    status_label: str(o, "status_label", "results"),
    code_revision: str(o, "code_revision", "results"),
    sources: arr(o, "sources", "results").map((v, i) => {
      const s = obj(v, `sources[${i}]`);
      const sha = str(s, "sha256", `sources[${i}]`);
      if (!/^[0-9a-f]{64}$/.test(sha)) throw new ResultsError(`sources[${i}].sha256: not a sha256`);
      return { path: str(s, "path", `sources[${i}]`), sha256: sha };
    }),
    experiments,
    assumptions: arr(o, "assumptions", "results").map((v, i) => {
      const a = obj(v, `assumptions[${i}]`);
      return {
        name: str(a, "name", `assumptions[${i}]`),
        value: str(a, "value", `assumptions[${i}]`),
        source: str(a, "source", `assumptions[${i}]`),
      };
    }),
    limitations: strArr(o, "limitations", "results"),
  };
}

const VERDICTS = new Set(["invalidated"]);

function nonEmpty<T>(a: T[], where: string): T[] {
  if (a.length === 0) throw new ResultsError(`${where}: empty`);
  return a;
}

/** Core schema plus the MARKET extensions; any missing or malformed field throws. */
export function validateResults(raw: unknown): MarketResults {
  const core = validateCore(raw);
  const o = obj(raw, "results");
  const h = obj(o.headline, "headline");
  const headline: Headline = {
    frozen_verdict: str(h, "frozen_verdict", "headline"),
    frozen_text: str(h, "frozen_text", "headline"),
    secondary_reading: str(h, "secondary_reading", "headline"),
    secondary_text: str(h, "secondary_text", "headline"),
  };
  if (!VERDICTS.has(headline.frozen_verdict)) throw new ResultsError(`headline.frozen_verdict: unexpected "${headline.frozen_verdict}"`);
  if (!core.experiments[0].verdict.startsWith(headline.frozen_verdict)) {
    throw new ResultsError("headline.frozen_verdict does not match the EXP-001 verdict");
  }
  const not_measured = arr(o, "not_measured", "results").map((v, i) => {
    const w = `not_measured[${i}]`;
    const n = obj(v, w);
    return { exp_id: str(n, "exp_id", w), outcome: str(n, "outcome", w), status: str(n, "status", w), reason: str(n, "reason", w) };
  });
  const g = obj(o.exploratory_dt_grid, "exploratory_dt_grid");
  const contrasts = nonEmpty(strArr(g, "contrasts", "exploratory_dt_grid"), "exploratory_dt_grid.contrasts");
  const label = str(g, "label", "exploratory_dt_grid");
  if (!/^EXPLORATORY/.test(label)) throw new ResultsError("exploratory_dt_grid.label must say EXPLORATORY");
  const dtGrid: DtGrid = {
    label,
    source: str(g, "source", "exploratory_dt_grid"),
    claim_ids: strArr(g, "claim_ids", "exploratory_dt_grid"),
    unit: str(g, "unit", "exploratory_dt_grid"),
    contrasts,
    rows: nonEmpty(arr(g, "rows", "exploratory_dt_grid"), "exploratory_dt_grid.rows").map((v, i) => {
      const w = `exploratory_dt_grid.rows[${i}]`;
      const r = obj(v, w);
      const cells = arr(r, "cells", w).map((x, j) => estimate(x, `${w}.cells[${j}]`));
      if (cells.length !== contrasts.length) throw new ResultsError(`${w}: one cell per contrast expected`);
      cells.forEach((c, j) => {
        if (c.ci_low === null || c.display === null || c.interval_display === null) throw new ResultsError(`${w}.cells[${j}]: interval and display text required`);
      });
      return { dt: num(r, "dt", w) as number, cells };
    }),
  };
  const m = obj(o.mid_paths, "mid_paths");
  const midPaths: MidPaths = {
    label: str(m, "label", "mid_paths"),
    unit: str(m, "unit", "mid_paths"),
    source: str(m, "source", "mid_paths"),
    burn_in: num(m, "burn_in", "mid_paths") as number,
    arms: nonEmpty(arr(m, "arms", "mid_paths"), "mid_paths.arms").map((v, i) => {
      const w = `mid_paths.arms[${i}]`;
      const a = obj(v, w);
      const mid = nonEmpty(arr(a, "mid", w), `${w}.mid`).map((x, j) => {
        if (typeof x !== "number" || !Number.isFinite(x) || x <= 0) throw new ResultsError(`${w}.mid[${j}]: expected a positive finite number`);
        return x;
      });
      const every = num(a, "every", w) as number;
      if (!Number.isInteger(every) || every < 1) throw new ResultsError(`${w}.every: expected a positive integer`);
      return { arm: str(a, "arm", w), label: str(a, "label", w), run_id: str(a, "run_id", w), every, mid };
    }),
  };
  for (const e of core.experiments) {
    for (const x of e.estimates) {
      if (x.display === null) throw new ResultsError(`${e.id}: every published estimate needs its manuscript display text`);
      if (x.ci_low !== null && x.interval_display === null) throw new ResultsError(`${e.id}: an interval needs its manuscript display text`);
    }
  }
  return { ...core, headline, not_measured, exploratory_dt_grid: dtGrid, mid_paths: midPaths };
}

export async function loadResults(url = "./data/results.json"): Promise<MarketResults> {
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) throw new ResultsError(`could not load ${url} (HTTP ${res.status})`);
  let raw: unknown;
  try {
    raw = await res.json();
  } catch {
    throw new ResultsError(`${url} is not valid JSON`);
  }
  return validateResults(raw);
}

/** Formats a number for display without inventing precision. */
export function fmt(x: number, digits = 3): string {
  if (Number.isInteger(x)) return x.toString();
  return Number(x.toPrecision(digits)).toString();
}

export function fmtEstimate(e: Estimate, digits = 3): string {
  return e.display ?? `${fmt(e.estimate, digits)}${e.unit ? " " + e.unit : ""}`;
}

export function fmtInterval(e: Estimate, digits = 3): string {
  if (e.interval_display !== null) return e.interval_display;
  if (e.ci_low === null || e.ci_high === null) return "no interval";
  const level = e.ci_level === null ? "" : `${Math.round(e.ci_level * 100)}% `;
  return `${level}[${fmt(e.ci_low, digits)}, ${fmt(e.ci_high, digits)}]`;
}

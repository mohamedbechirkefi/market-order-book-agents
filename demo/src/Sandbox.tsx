// SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0
// Visitor sandbox: runs the TypeScript port of the research engine in a Web Worker. Its output
// is labelled as sandbox output and never mixed with the published results.
import { useEffect, useRef, useState } from "react";
import { BookLadder, domainOf, PricePanel } from "./charts";
import { fmt } from "./results";
import { SEED_MAX, SEED_MIN, SNAPSHOT_EVERY, type SandboxSettings, type WorkerReply, type WorkerRequest } from "./sandboxShared";

type Done = Extract<WorkerReply, { type: "done" }>;

const PRESETS: { key: string; label: string; c: SandboxSettings["composition"] }[] = [
  { key: "A0", label: "A0: 100 random-order", c: { ZI: 100, TF: 0, MR: 0, PA: 0 } },
  { key: "A1", label: "A1: 30 trend followers", c: { ZI: 70, TF: 30, MR: 0, PA: 0 } },
  { key: "A2", label: "A2: 30 mean reverters", c: { ZI: 70, TF: 0, MR: 30, PA: 0 } },
  { key: "A3", label: "A3: 15 TF and 15 MR", c: { ZI: 70, TF: 15, MR: 15, PA: 0 } },
  { key: "A4", label: "A4: 30 placebo", c: { ZI: 70, TF: 0, MR: 0, PA: 30 } },
];

const DEFAULTS: SandboxSettings = { composition: { ZI: 70, TF: 30, MR: 0, PA: 0 }, steps: 100_000, zi_market_prob: 0.2, shock: false };
const DEFAULT_SEED = 1;
const LIQUIDITY = [
  { v: 0.35, label: "low (ZI market-order probability 0.35)" },
  { v: 0.2, label: "medium, frozen value (0.2)" },
  { v: 0.1, label: "high (0.1)" },
];

const show = (x: number | null, d = 4) => (x === null ? "undefined" : fmt(x, d));

export function Sandbox() {
  const worker = useRef<Worker | null>(null);
  const [settings, setSettings] = useState<SandboxSettings>(DEFAULTS);
  const [seed, setSeed] = useState(DEFAULT_SEED);
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [message, setMessage] = useState("");
  const [result, setResult] = useState<Done | null>(null);
  const [step, setStep] = useState(0);

  useEffect(() => {
    const w = new Worker(new URL("./sandbox.worker.ts", import.meta.url), { type: "module" });
    w.onmessage = (ev: MessageEvent<WorkerReply>) => {
      const m = ev.data;
      if (m.type === "progress") {
        setProgress(m.fraction);
        return;
      }
      setRunning(false);
      if (m.type === "done") {
        setResult(m);
        const last = m.snapshots[m.snapshots.length - 1].step;
        setStep(last);
        setMessage(
          `Sandbox output (your run, seed ${m.seed}, ${m.settings.steps.toLocaleString("en")} steps): VCI at dt 50 = ${show(m.metrics.vci)}; ` +
            `mean spread ${show(m.metrics.mean_spread)} price units; invariants ${m.invariants_passed ? "held" : "violated"}.`,
        );
      }
      if (m.type === "error") setMessage(`Sandbox run failed: ${m.message}`);
      if (m.type === "cancelled") setMessage("Sandbox run cancelled.");
    };
    worker.current = w;
    return () => w.terminate();
  }, []);

  const c = settings.composition;
  const strategic = c.TF + c.MR + c.PA;
  const valid = strategic <= 99 && Number.isInteger(seed) && seed >= SEED_MIN && seed <= SEED_MAX;

  const setCount = (k: "TF" | "MR" | "PA", v: number) => {
    const n = Math.max(0, Math.min(99, Math.round(Number.isFinite(v) ? v : 0)));
    const next = { ...c, [k]: n };
    next.ZI = Math.max(0, 100 - next.TF - next.MR - next.PA);
    setSettings({ ...settings, composition: next });
  };

  const run = () => {
    if (!valid) return;
    setRunning(true);
    setProgress(0);
    setMessage("");
    worker.current?.postMessage({ type: "run", seed, settings } satisfies WorkerRequest);
  };
  const cancel = () => worker.current?.postMessage({ type: "cancel" } satisfies WorkerRequest);
  const reset = () => {
    if (running) cancel();
    setSettings(DEFAULTS);
    setSeed(DEFAULT_SEED);
    setResult(null);
    setMessage("");
    setProgress(0);
    setStep(0);
  };

  const snap = result ? result.snapshots[Math.min(result.snapshots.length - 1, Math.round(step / SNAPSHOT_EVERY))] : null;
  const m = result?.metrics;

  return (
    <section id="sandbox" aria-labelledby="h-sandbox" className="sandbox">
      <div className="pit-band">
        <h2 id="h-sandbox">The pit: run the order book yourself</h2>
        <p className="tag tag-sandbox">Sandbox: your run, not a research result</p>
      </div>
      <div className="pit-body">
      <p>
        This runs the study's engine in your browser: a TypeScript port of <code>src/market/</code> (order book, accounting, agents,
        random streams). On the test fixture it reproduces the Python engine exactly, price by price (see Method). It runs one
        seed at a time, so it has no interval; the published results above use 30 paired seeds. Seeds are limited to the
        development range {SEED_MIN} to {SEED_MAX}; the confirmatory seeds are not offered.
      </p>

      <fieldset className="controls-block">
        <legend>Agent composition (100 agents; random-order agents fill the rest)</legend>
        <div className="presets" role="group" aria-label="Preset compositions from the study">
          {PRESETS.map((p) => (
            <button
              type="button"
              key={p.key}
              aria-pressed={c.ZI === p.c.ZI && c.TF === p.c.TF && c.MR === p.c.MR && c.PA === p.c.PA}
              onClick={() => setSettings({ ...settings, composition: { ...p.c } })}
            >
              {p.label}
            </button>
          ))}
        </div>
        <div className="controls">
          <label>
            Trend followers
            <input id="sb-tf" type="number" min={0} max={99} value={c.TF} onChange={(e) => setCount("TF", Number(e.target.value))} />
          </label>
          <label>
            Mean reverters
            <input id="sb-mr" type="number" min={0} max={99} value={c.MR} onChange={(e) => setCount("MR", Number(e.target.value))} />
          </label>
          <label>
            Placebo aggressive
            <input id="sb-pa" type="number" min={0} max={99} value={c.PA} onChange={(e) => setCount("PA", Number(e.target.value))} />
          </label>
          <p className="zi-count">
            Random-order: <strong>{c.ZI}</strong>
          </p>
        </div>
        {strategic > 99 && <p className="warn">At least one random-order agent is needed to seed the book.</p>}
      </fieldset>

      <div className="controls">
        <label>
          Liquidity supply
          <select id="sb-liquidity" value={settings.zi_market_prob} onChange={(e) => setSettings({ ...settings, zi_market_prob: Number(e.target.value) })}>
            {LIQUIDITY.map((l) => (
              <option key={l.v} value={l.v}>
                {l.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          Run length
          <select id="sb-steps" value={settings.steps} onChange={(e) => setSettings({ ...settings, steps: Number(e.target.value) })}>
            <option value={20000}>20,000 steps</option>
            <option value={50000}>50,000 steps</option>
            <option value={100000}>100,000 steps (frozen length)</option>
          </select>
        </label>
        <label className="check">
          <input id="sb-shock" type="checkbox" checked={settings.shock} onChange={(e) => setSettings({ ...settings, shock: e.target.checked })} />
          Sell shock at mid-run (50% of resting bid depth)
        </label>
        <label>
          Seed ({SEED_MIN} to {SEED_MAX})
          <input
            id="sb-seed"
            type="number"
            min={SEED_MIN}
            max={SEED_MAX}
            value={seed}
            onChange={(e) => setSeed(Math.trunc(Number(e.target.value)))}
            aria-invalid={!valid}
          />
        </label>
      </div>
      <div className="controls">
        <button type="button" className="primary" onClick={run} disabled={running || !valid}>
          Run
        </button>
        <button type="button" onClick={cancel} disabled={!running}>
          Cancel
        </button>
        <button type="button" onClick={reset}>
          Reset
        </button>
        {running && <progress max={1} value={progress} aria-label="Sandbox run progress" />}
      </div>
      <p className="note">Burn-in is fixed at 10,000 steps and returns are sampled every 50 steps, as in the frozen protocol.</p>

      <p aria-live="polite" className="sandbox-out">
        {message}
      </p>

      {result && m && snap && (
        <div className="sandbox-result" key={`${result.seed}-${result.runtime_ms}`}>
          <div className="sandbox-grid">
            <figure>
              <figcaption>
                Sandbox price chart: mid price (price units) against event time, every {result.every} steps. Shaded: burn-in.
                {result.shock && " Dotted line: the sell shock."} Solid vertical line: the step shown in the order book.
              </figcaption>
              <PricePanel
                path={{ key: "sandbox", title: "Sandbox run", every: result.every, mid: result.mid }}
                yDomain={domainOf([{ mid: result.mid }])}
                burnIn={10_000}
                marker={snap.step}
                shockStep={result.shock?.step ?? null}
              />
            </figure>
            <div>
              <label className="scrub">
                Order book at step <strong className="mono">{snap.step.toLocaleString("en")}</strong>
                <input
                  id="sb-step"
                  type="range"
                  min={0}
                  max={result.settings.steps}
                  step={SNAPSHOT_EVERY}
                  value={snap.step}
                  onChange={(e) => setStep(Number(e.target.value))}
                  aria-valuetext={`step ${snap.step}`}
                />
              </label>
              <BookLadder snap={snap} caption="Ten best price levels per side (sandbox). Bars: resting units at each price." />
            </div>
          </div>
          <div className="table-scroll" id="tbl-sandbox" role="region" aria-label="Sandbox run metrics" tabIndex={0}>
            <table>
              <caption>Sandbox metrics for this one run (after burn-in; no interval, one seed)</caption>
              <tbody>
                <tr><th scope="row">VCI at dt 50 (dimensionless)</th><td className="mono">{show(m.vci)}</td></tr>
                <tr><th scope="row">Realised volatility (log return per 50 steps)</th><td className="mono">{show(m.realised_volatility)}</td></tr>
                <tr><th scope="row">acf(r, 1)</th><td className="mono">{show(m.return_acf1)}</td></tr>
                <tr><th scope="row">Mean quoted spread (price units)</th><td className="mono">{show(m.mean_spread)}</td></tr>
                <tr><th scope="row">Mean depth at best (units)</th><td className="mono">{show(m.mean_depth_at_best)}</td></tr>
                <tr><th scope="row">Maximum drawdown (fraction)</th><td className="mono">{show(m.max_drawdown)}</td></tr>
                <tr><th scope="row">One-sided book (fraction of steps)</th><td className="mono">{show(m.one_sided_fraction)}</td></tr>
                <tr><th scope="row">Degenerate under the protocol's flag</th><td>{m.degenerate ? "yes" : "no"}</td></tr>
                <tr><th scope="row">Accounting and book invariants</th><td>{result.invariants_passed ? "held" : "violated"}</td></tr>
                <tr><th scope="row">Run time in this browser</th><td className="mono">{Math.round(result.runtime_ms)} ms</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      )}
      <p className="note">
        Nothing you run here is stored or sent anywhere. Sandbox output is a simulation of a toy market under the stated
        assumptions; it is not investment advice and not a statement about any real market.
      </p>
      </div>
    </section>
  );
}

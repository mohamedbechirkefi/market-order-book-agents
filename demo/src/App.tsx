// SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0
import { useEffect, useState } from "react";
import { domainOf, IntervalPlot, PricePanel, type IntervalRow } from "./charts";
import { fmtEstimate, fmtInterval, loadResults, ResultsError, type Estimate, type MarketResults } from "./results";
import { Sandbox } from "./Sandbox";

type State = { kind: "loading" } | { kind: "error"; message: string } | { kind: "ready"; results: MarketResults };

export function App() {
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    loadResults()
      .then((results) => setState({ kind: "ready", results }))
      .catch((e: unknown) =>
        setState({ kind: "error", message: e instanceof ResultsError ? e.message : "results could not be loaded" }),
      );
  }, []);

  return (
    <>
      <a className="skip" href="#main">Skip to content</a>
      <header className="site">
        <div className="wrap">
          <p className="kicker">MARKET · a preregistered simulation study of a limit-order book</p>
          <h1>Do trend followers raise volatility clustering in a simulated order book?</h1>
          <nav aria-label="Sections">
            <a href="#overview">Overview</a>
            <a href="#results">Results</a>
            <a href="#exploratory">Exploratory</a>
            <a href="#assumptions">Assumptions</a>
            <a href="#method">Method and limitations</a>
            <a href="#sandbox">Sandbox</a>
          </nav>
        </div>
      </header>
      <main id="main" className="wrap">
        {state.kind === "loading" && <p role="status">Loading the published results.</p>}
        {state.kind === "error" && (
          <div role="alert" className="panel error">
            <h2>Results unavailable</h2>
            <p>The published results file failed validation, so no numbers are shown.</p>
            <p>
              <code>{state.message}</code>
            </p>
          </div>
        )}
        {state.kind === "ready" && <Published r={state.results} />}
        <Sandbox />
      </main>
      <footer className="site">
        <div className="wrap">
          <p>
            Runs offline after the first load. No data about visitors is collected, stored or sent anywhere. Simulated markets
            only: nothing on this page is investment advice, a prediction or a claim about real markets.
          </p>
          <p>
            Mohamed Bechir Kefi, independent researcher. Repository: https://github.com/mohamedbechirkefi/market-order-book-agents. Demo: https://market-order-book-agents.kefimohamedbechir.workers.dev. Licence: MARKET Source-Available Non-Commercial Research
            License v1.0.
          </p>
        </div>
      </footer>
    </>
  );
}

const row = (key: string, label: string, e: Estimate, note?: string): IntervalRow => ({
  key,
  label,
  note,
  estimate: e.estimate,
  lo: e.ci_low as number,
  hi: e.ci_high as number,
  display: fmtEstimate(e),
  interval_display: fmtInterval(e),
});

function Published({ r }: { r: MarketResults }) {
  const exp = Object.fromEntries(r.experiments.map((e) => [e.id, e]));
  const e1 = exp["EXP-001"].estimates;
  const e4 = exp["EXP-004"].estimates;
  const by = (es: Estimate[], prefix: string) => {
    const f = es.find((x) => x.label.startsWith(prefix));
    if (!f || f.ci_low === null) throw new ResultsError(`missing estimate "${prefix}"`);
    return f;
  };
  const verdictRows: IntervalRow[] = [
    row("p", "dt 50 steps (primary, EXP-001)", by(e1, "VCI(A1) - VCI(A0)"), "sign reference of the rule"),
    row("d10", "dt 10 steps (EXP-004)", by(e4, "sampling interval dt 10"), "opposite sign, excludes 0"),
    row("d200", "dt 200 steps (EXP-004)", by(e4, "sampling interval dt 200"), "opposite sign, excludes 0"),
    row("t2", "tick 2 (EXP-004)", by(e4, "tick 2"), "includes 0"),
  ];
  const placeboRows: IntervalRow[] = [
    row("pl", "A1 minus placebo A4", by(e4, "placebo")),
    row("a4", "placebo A4 minus A0", by(e4, "descriptive")),
  ];
  const grid = r.exploratory_dt_grid;
  const gridRows: IntervalRow[] = grid.rows.map((g) => row(`g${g.dt}`, `dt ${g.dt} steps`, g.cells[0]));
  const paths = r.mid_paths.arms.map((a) => ({ key: a.arm, title: a.label, every: a.every, mid: a.mid }));
  const yDomain = domainOf(paths);

  return (
    <>
      <section id="overview" aria-labelledby="h-overview">
        <h2 id="h-overview">Overview</h2>
        <div className="verdict" role="note" aria-label="Frozen verdict">
          <p className="tag tag-measured">Measured, confirmatory</p>
          <p className="verdict-word">Frozen verdict: {r.headline.frozen_verdict}</p>
          <p>{r.headline.frozen_text}</p>
        </div>
        <div className="secondary-reading">
          <p className="tag tag-exploratory">Secondary reading, exploratory</p>
          <p>{r.headline.secondary_text}</p>
        </div>
        <p className="status-label">{r.status_label}</p>
        <p>
          <strong>Question.</strong> {r.question}
        </p>
        <div className="legend-labels" aria-label="How values are labelled on this page">
          <span className="tag tag-measured">Measured</span> confirmatory results from committed runs.
          <span className="tag tag-exploratory">Exploratory</span> post hoc checks, never a verdict.
          <span className="tag tag-assumption">Assumption</span> model inputs, not results.
          <span className="tag tag-sandbox">Sandbox</span> your own run in this browser.
        </div>
      </section>

      <section id="results" aria-labelledby="h-results">
        <p className="tag tag-measured">Measured, confirmatory</p>
        <h2 id="h-results">Published results</h2>
        <p className="note">
          Every number is printed exactly as in the manuscript (<code>research/paper/manuscript.md</code>), from the committed
          results of code revision <code>{r.code_revision.slice(0, 7)}</code>: 95% percentile bootstrap intervals over 30 paired
          seeds unless the row says Holm interval. None of it comes from the sandbox below.
        </p>

        <figure className="panel">
          <figcaption id="fig-rule-cap">
            <strong>Why the verdict is "invalidated".</strong> The trend-follower effect on volatility clustering, VCI(A1) minus
            VCI(A0), at the preregistered sampling interval and in the three frozen robustness components. Tick mark: mean
            paired difference over 30 seeds; whiskers: 95% interval; vertical line: zero. At 50 steps the estimate is near zero
            and its interval includes 0; at 10 and 200 steps it is positive with intervals excluding 0, which the frozen rule
            reads as a sign reversal.
          </figcaption>
          <IntervalPlot id="fig-rule" rows={verdictRows} axisLabel="VCI difference (dimensionless)" />
        </figure>

        <figure className="panel">
          <figcaption id="fig-placebo-cap">
            <strong>Aggressiveness-matched placebo (EXP-004, dt 50).</strong> Price-independent aggressive agents raised VCI
            relative to the random-order baseline, and trend followers added nothing beyond them; the upper end of the first
            interval is close to 0, so "less clustering than the placebo" is not claimed.
          </figcaption>
          <IntervalPlot id="fig-placebo" rows={placeboRows} axisLabel="VCI difference (dimensionless)" />
        </figure>

        <h3 className="cards-title">Every registered experiment</h3>
        <div className="cards">
          {r.experiments.map((e) => (
            <article key={e.id} className="panel card" aria-labelledby={`h-${e.id}`}>
              <h3 id={`h-${e.id}`}>
                {e.id}: {e.title}
              </h3>
              <p className="meta">{e.status}</p>
              <p className="card-verdict">
                <strong>Verdict under the frozen rule:</strong> {e.verdict}
              </p>
              <div className="table-scroll" id={`tbl-${e.id}`} role="region" aria-label={`${e.id} estimates`} tabIndex={0}>
                <table>
                  <thead>
                    <tr>
                      <th scope="col">Quantity</th>
                      <th scope="col">Estimate</th>
                      <th scope="col">Interval</th>
                    </tr>
                  </thead>
                  <tbody>
                    {e.estimates.map((x) => (
                      <tr key={x.label}>
                        <th scope="row">
                          {x.label}
                          {x.unit && <span className="muted"> ({x.unit})</span>}
                        </th>
                        <td className="mono">{fmtEstimate(x)}</td>
                        {x.interval_display !== null ? <td className="mono">{x.interval_display}</td> : <td className="muted">no interval reported</td>}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {e.notes.map((n, i) => (
                <p key={i} className="note">
                  {n}
                </p>
              ))}
              <p className="meta">
                Report: <code>{e.report_path}</code> · Claims: {e.claim_ids.join(", ")}
              </p>
            </article>
          ))}
          {r.not_measured.map((n) => (
            <article key={n.outcome} className="panel card not-measured" aria-label={`${n.exp_id}: ${n.outcome}`}>
              <h3>
                {n.exp_id}: {n.outcome}
              </h3>
              <p className="card-verdict">
                <strong>Status:</strong> {n.status}
              </p>
              <p className="note">{n.reason}</p>
            </article>
          ))}
        </div>

        <figure className="panel">
          <figcaption>
            <strong>Price paths (EXP-001, seed 1001, one run per arm).</strong> {r.mid_paths.label}. Mid price in price units
            against event time in steps, every {r.mid_paths.arms[0].every} steps; the shaded band is the burn-in, excluded from
            every metric. All four panels share one vertical scale. A single seed illustrates the arms; it is not an estimate.
          </figcaption>
          <div className="multiples">
            {paths.map((p) => (
              <div key={p.key}>
                <p className="panel-title">{p.title}</p>
                <PricePanel path={p} yDomain={yDomain} burnIn={r.mid_paths.burn_in} />
              </div>
            ))}
          </div>
        </figure>
      </section>

      <section id="exploratory" aria-labelledby="h-exploratory" className="exploratory">
        <p className="tag tag-exploratory">Exploratory, post hoc</p>
        <h2 id="h-exploratory">Exploratory: the effect across sampling intervals</h2>
        <p className="note">
          {grid.label}. Source <code>{grid.source}</code>; claims {grid.claim_ids.join(", ")}. These checks were designed after
          the confirmatory results were seen and are hypothesis-generating only.
        </p>
        <figure className="panel">
          <figcaption>
            <strong>VCI(A1) minus VCI(A0) by sampling interval</strong>, 30 development seeds, 95% percentile bootstrap
            intervals. The sign of the trend-follower contrast depends on the horizon: positive at short and long intervals,
            near zero in between. At long intervals trend runs, not only clustering, raise this statistic.
          </figcaption>
          <IntervalPlot id="fig-grid" rows={gridRows} axisLabel={grid.unit} />
        </figure>
        <div className="table-scroll" id="tbl-dt-grid" role="region" aria-label="Exploratory sampling-interval table" tabIndex={0}>
          <table>
            <caption>EXPLORATORY: VCI contrasts by sampling interval (mean difference and 95% interval)</caption>
            <thead>
              <tr>
                <th scope="col">dt (steps)</th>
                {grid.contrasts.map((c) => (
                  <th key={c} scope="col">
                    {c}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {grid.rows.map((g) => (
                <tr key={g.dt}>
                  <th scope="row">{g.dt}</th>
                  {g.cells.map((c) => (
                    <td key={c.label} className="mono">
                      {c.display} {c.interval_display}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section id="assumptions" aria-labelledby="h-assumptions">
        <p className="tag tag-assumption">Assumptions: model inputs, not results</p>
        <h2 id="h-assumptions">Assumptions</h2>
        <dl className="assumptions">
          {r.assumptions.map((a) => (
            <div key={a.name}>
              <dt>{a.name}</dt>
              <dd>
                {a.value} <span className="meta">({a.source})</span>
              </dd>
            </div>
          ))}
        </dl>
      </section>

      <section id="method" aria-labelledby="h-method">
        <h2 id="h-method">Method and limitations</h2>
        <p>
          Five experiments were registered and their protocols frozen by the owner before any confirmatory run. Arms that share
          a seed share their random streams, so every contrast is a mean of per-seed paired differences with a percentile
          bootstrap interval. The analysis module was committed before any confirmatory output existed. Reports, manuscript and
          this page are generated from the same committed outputs; a test checks that every number shown here is printed in
          the manuscript.
        </p>
        <p>
          The sandbox engine is a port, statement for statement, of the Python engine. A test compares it with a fixture made
          by the Python engine on six short development-seed runs: the random streams, every mid price, the event counts and the
          final balances are identical, and the metrics agree within 1e-9.
        </p>
        <h3>Limitations</h3>
        <ul>
          {r.limitations.map((l, i) => (
            <li key={i}>{l}</li>
          ))}
        </ul>
        <details>
          <summary>Source files and SHA-256</summary>
          <ul className="meta">
            {r.sources.map((s) => (
              <li key={s.path}>
                <code>{s.path}</code> <code>{s.sha256.slice(0, 12)}</code>
              </li>
            ))}
          </ul>
        </details>
      </section>
    </>
  );
}

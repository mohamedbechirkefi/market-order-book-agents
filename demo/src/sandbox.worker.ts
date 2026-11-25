// SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0
// Visitor sandbox: runs the TypeScript port of the research engine (src/engine/) for one
// configuration and one development seed, bounded to the frozen run length of 100,000 steps,
// cancellable. Nothing is sent anywhere; the result stays in this browser tab.
import { Cancelled, simulate, SimError } from "./engine/sim";
import { computeMetrics } from "./engine/metrics";
import { SEED_MAX, SEED_MIN, SERIES_EVERY, SNAPSHOT_EVERY, toConfig, type WorkerReply, type WorkerRequest } from "./sandboxShared";

let cancelled = false;

onmessage = async (ev: MessageEvent<WorkerRequest>) => {
  const m = ev.data;
  if (m.type === "cancel") {
    cancelled = true;
    return;
  }
  cancelled = false;
  const t0 = performance.now();
  try {
    if (!Number.isInteger(m.seed) || m.seed < SEED_MIN || m.seed > SEED_MAX) throw new SimError(`seed must be an integer from ${SEED_MIN} to ${SEED_MAX}`);
    const cfg = toConfig(m.settings);
    const out = await simulate(cfg, m.seed, {
      snapshotEvery: SNAPSHOT_EVERY,
      snapshotLevels: 10,
      progressEvery: 5_000,
      onProgress: async (t) => {
        postMessage({ type: "progress", fraction: t / cfg.steps } satisfies WorkerReply);
        await new Promise((r) => setTimeout(r, 0)); // let a cancel message in
        return !cancelled;
      },
    });
    const mid: number[] = [];
    for (let i = 0; i < out.mid.length; i += SERIES_EVERY) mid.push(out.mid[i]);
    postMessage({
      type: "done",
      seed: m.seed,
      settings: m.settings,
      every: SERIES_EVERY,
      mid,
      snapshots: out.snapshots,
      metrics: computeMetrics(out),
      shock: out.shock ? { step: out.shock.step, qty: out.shock.qty, filled: out.shock.filled } : null,
      invariants_passed: out.invariants_passed,
      runtime_ms: performance.now() - t0,
    } satisfies WorkerReply);
  } catch (e) {
    if (e instanceof Cancelled) postMessage({ type: "cancelled" } satisfies WorkerReply);
    else postMessage({ type: "error", message: e instanceof Error ? e.message : String(e) } satisfies WorkerReply);
  }
};

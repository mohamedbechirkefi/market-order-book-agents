// SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0
// The sandbox port against the Python research engine (fixture from scripts/make_demo_fixture.py,
// development seeds only). Tolerance: the random streams, every recorded price, mid, depth,
// volume, count and final balance must be identical (exact equality); the floating-point
// metrics must agree within 1e-9 absolute, because sums run in a different order from numpy.
import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { makeStreams, STREAM_NAMES } from "./rng";
import { simulate, validateConfig, DEFAULT_CONFIG, SimError, type SimConfig } from "./sim";
import { computeMetrics, type RunMetrics } from "./metrics";

const fx = JSON.parse(readFileSync("src/engine/fixture.json", "utf8"));
const TOL = 1e-9;

const checks = (a: ArrayLike<number>) => {
  let sum = 0;
  let weighted = 0;
  for (let i = 0; i < a.length; i++) {
    sum += a[i];
    weighted += i * a[i];
  }
  return { sum, weighted };
};

describe("random streams", () => {
  it("are bit-identical to numpy SeedSequence + PCG64", () => {
    const s = makeStreams(fx.rng_seed);
    for (const k of STREAM_NAMES) expect([0, 1, 2, 3, 4].map(() => s[k].uniform())).toEqual(fx.rng_first_uniforms[k]);
  });
});

describe("engine port matches the Python engine", () => {
  for (const c of fx.cases) {
    it(c.name, async () => {
      const out = await simulate(c.config as SimConfig, c.seed);
      expect(Array.from(out.mid)).toEqual(c.mid);
      expect(checks(out.best_bid)).toEqual(c.best_bid);
      expect(checks(out.best_ask)).toEqual(c.best_ask);
      expect(checks(out.depth_best)).toEqual(c.depth_best);
      expect(checks(out.volume)).toEqual(c.volume);
      expect(out.counts).toEqual(c.counts);
      expect(out.final_cash).toEqual(c.final_cash);
      expect(out.final_inventory).toEqual(c.final_inventory);
      expect(out.shock).toEqual(c.shock);
      expect(out.invariants_passed).toBe(true);
      const m = computeMetrics(out);
      for (const [k, v] of Object.entries(c.metrics)) {
        const got = m[k as keyof RunMetrics];
        if (v === null) expect(got).toBeNull();
        else expect(Math.abs((got as number) - (v as number))).toBeLessThanOrEqual(TOL);
      }
      expect(m.degenerate).toBe(c.degenerate);
    });
  }
});

describe("invalid inputs", () => {
  it("rejects a composition with no agent", () => {
    expect(() => validateConfig({ ...DEFAULT_CONFIG, composition: { ZI: 0, TF: 0, MR: 0, PA: 0 } })).toThrow(SimError);
  });
  it("rejects burn-in at or above the run length", () => {
    expect(() => validateConfig({ ...DEFAULT_CONFIG, steps: 100, burn_in: 100 })).toThrow(SimError);
  });
  it("rejects a probability outside [0, 1]", () => {
    expect(() => validateConfig({ ...DEFAULT_CONFIG, zi_market_prob: 1.5 })).toThrow(SimError);
  });
  it("rejects a negative seed", async () => {
    await expect(simulate({ ...DEFAULT_CONFIG, steps: 50, burn_in: 10 }, -1)).rejects.toThrow();
  });
});

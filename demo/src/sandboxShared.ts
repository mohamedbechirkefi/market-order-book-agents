// SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0
// Types and bounds shared by the sandbox page and its Web Worker (no side effects).
import { DEFAULT_CONFIG, SimError, type BookSnapshot, type Composition, type SimConfig } from "./engine/sim";
import type { RunMetrics } from "./engine/metrics";

export interface SandboxSettings {
  composition: Composition;
  steps: number;
  zi_market_prob: number;
  shock: boolean;
}

export type WorkerRequest = { type: "run"; seed: number; settings: SandboxSettings } | { type: "cancel" };
export type WorkerReply =
  | { type: "progress"; fraction: number }
  | {
      type: "done";
      seed: number;
      settings: SandboxSettings;
      every: number;
      mid: number[];
      snapshots: BookSnapshot[];
      metrics: RunMetrics;
      shock: { step: number; qty: number; filled: number } | null;
      invariants_passed: boolean;
      runtime_ms: number;
    }
  | { type: "cancelled" }
  | { type: "error"; message: string };

export const MAX_STEPS = 100_000;
export const SEED_MIN = 1;
export const SEED_MAX = 999; // development seeds only; confirmatory seeds 1001..1030 are not offered
export const SERIES_EVERY = 100;
export const SNAPSHOT_EVERY = 1_000;

export function toConfig(s: SandboxSettings): SimConfig {
  if (!Number.isInteger(s.steps) || s.steps < 20_000 || s.steps > MAX_STEPS) throw new SimError("run length must be 20,000 to 100,000 steps");
  return {
    ...DEFAULT_CONFIG,
    composition: { ...s.composition },
    steps: s.steps,
    zi_market_prob: s.zi_market_prob,
    shock_step: s.shock ? Math.floor(s.steps / 2) : null,
  };
}


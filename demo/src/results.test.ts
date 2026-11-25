// SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0
import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { ResultsError, validateResults } from "./results";

const good = () => JSON.parse(readFileSync("public/data/results.json", "utf8"));

describe("validateResults", () => {
  it("accepts the exported results file", () => {
    expect(validateResults(good()).experiments.length).toBeGreaterThan(0);
  });
  it("rejects a wrong schema name", () => {
    expect(() => validateResults({ ...good(), schema: "other" })).toThrow(ResultsError);
  });
  it("rejects an unsupported major version", () => {
    expect(() => validateResults({ ...good(), schema_version: "2.0.0" })).toThrow(ResultsError);
  });
  it("rejects a missing estimate", () => {
    const r = good();
    delete r.experiments[0].estimates?.[0]?.estimate;
    if (r.experiments[0].estimates.length === 0) r.experiments[0].title = 7;
    expect(() => validateResults(r)).toThrow(ResultsError);
  });
  it("rejects a non-finite number", () => {
    const r = good();
    r.experiments[0].estimates = [{ label: "x", estimate: "NaN", ci_low: null, ci_high: null, ci_level: null, unit: "" }];
    expect(() => validateResults(r)).toThrow(ResultsError);
  });
  it("rejects a half-open interval", () => {
    const r = good();
    r.experiments[0].estimates = [{ label: "x", estimate: 1, ci_low: 0, ci_high: null, ci_level: 0.95, unit: "" }];
    expect(() => validateResults(r)).toThrow(ResultsError);
  });
  it("rejects a malformed source hash", () => {
    expect(() => validateResults({ ...good(), sources: [{ path: "a", sha256: "zz" }] })).toThrow(ResultsError);
  });
  it("rejects a missing headline", () => {
    const r = good();
    delete r.headline;
    expect(() => validateResults(r)).toThrow(ResultsError);
  });
  it("rejects a headline verdict other than the frozen one", () => {
    const r = good();
    r.headline.frozen_verdict = "qualified";
    expect(() => validateResults(r)).toThrow(ResultsError);
  });
  it("rejects an EXP-001 verdict that does not lead with the frozen verdict", () => {
    const r = good();
    r.experiments[0].verdict = "inconclusive";
    expect(() => validateResults(r)).toThrow(ResultsError);
  });
  it("rejects an estimate without its manuscript display text", () => {
    const r = good();
    r.experiments[0].estimates[0].display = null;
    expect(() => validateResults(r)).toThrow(ResultsError);
  });
  it("rejects an exploratory grid that is not labelled exploratory", () => {
    const r = good();
    r.exploratory_dt_grid.label = "Results by dt";
    expect(() => validateResults(r)).toThrow(ResultsError);
  });
  it("rejects a grid cell without an interval", () => {
    const r = good();
    r.exploratory_dt_grid.rows[0].cells[0].ci_low = null;
    r.exploratory_dt_grid.rows[0].cells[0].ci_high = null;
    expect(() => validateResults(r)).toThrow(ResultsError);
  });
  it("rejects a non-positive mid price in the published paths", () => {
    const r = good();
    r.mid_paths.arms[0].mid[3] = 0;
    expect(() => validateResults(r)).toThrow(ResultsError);
  });
  it("rejects a malformed not-measured entry", () => {
    const r = good();
    r.not_measured[0].reason = "";
    expect(() => validateResults(r)).toThrow(ResultsError);
  });
  it("leads with the frozen verdict and keeps every registered experiment", () => {
    const r = validateResults(good());
    expect(r.headline.frozen_verdict).toBe("invalidated");
    expect(r.experiments.map((e) => e.id)).toEqual(["EXP-001", "EXP-002", "EXP-003", "EXP-004", "EXP-005"]);
  });
});

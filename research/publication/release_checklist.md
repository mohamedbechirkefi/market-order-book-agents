<!-- SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0 -->
# Release checklist (M6). Nothing is checked at M0.

**Status (2026-11-25):** release candidate prepared in M6. Each ticked item was verified by the AI assistant in that session; the evidence is next to it. The two owner items stay unticked.

**Update (2026-11-26):** the repository was pushed by the coordinator on the owner's word and has been public at https://github.com/mohamedbechirkefi/market-order-book-agents since 2026-11-25; the demo is to be hosted at https://market-order-book-agents.kefimohamedbechir.workers.dev (Cloudflare Workers static assets, free plan, deployed by the coordinator; owner, 2026-11-26, decision sheet B2). No release, tag or DOI exists yet (B18, after the owner's full-text review B16). The owner's answers of 2026-11-26 are recorded in `author_review.md` and decision D-021.

- [x] Clean clone into a separate directory; `uv sync --frozen` succeeds (output recorded). Evidence: `reproducibility_report.md` section 2 (clone of 704a568, `uv sync --frozen --all-groups --all-extras`, then `Audited 9 packages`).
- [x] Full test suite run; actual counts recorded in progress.md. Evidence: clean clone `170 passed`; working repository after M6 `176 passed` (`progress.md`, session 10); demo `27 passed`.
- [x] Smoke reproduction matches committed summary within documented tolerance. Evidence: `reproducibility_report.md` section 3 (every metric identical to `results/exploratory/smoke-M3/`; only runtimes differ).
- [x] Demo builds and works offline after load. Evidence: `npm run build` ok and `node tools/a11y_check.mjs dist` -> `A11Y-CHECK PASS`, including "offline after first load" (clean clone and working repository).
- [x] data/manifest.json and artifact_manifest.json verified; all links resolve. Evidence: FI-2010 files match their SHA-256 and sizes; 550 of 550 result checksums OK; all 6,495 manifest result paths and 21 figure paths exist; `scripts/check_links.py` -> `LINK-CHECK PASS` (`tests/test_links.py`).
- [x] Secret and personal-identifier scan clean. Evidence: over the tracked files, 0 e-mail addresses, 0 private-key headers or token patterns, 0 `.env` files, and no e-mail or local path in the PDFs; absolute home-directory paths reduced from 28 lines in 21 files to 15 lines in 8 files, each remaining one recorded with its reason (`reproducibility_report.md` section 5).
- [x] Licence headers present; third-party licences recorded. Evidence: every tracked Markdown, Python, TypeScript, CSS, HTML, CFF, TOML, YAML, BibTeX and LaTeX file carries the SPDX header except the licence files and `master_prompt.md` (excluded by rule); generated SVG figures, logs and data fixtures carry none (generated outputs; JSON and CSV are covered by `NOTICE.md`). Third-party licences: `dependency_licences.md` (two external tools flagged for the owner).
- [x] Manuscript and report PDFs compiled (pandoc to Typst) and visually inspected. Evidence: `scripts/build_pdfs.py` -> `manuscript.pdf` 20 pages, `supplementary.pdf` 3, reports 8, 7, 5, 5, 5; every manuscript and supplement page and the first page and every figure page of each report rendered to PNG and inspected; fixes in `reproducibility_report.md` section 5; PDF titles set, no e-mail, no local path; each under 0.4 MB; rebuild byte-identical.
- [x] Claims audit complete (claims_audit.md). Evidence: `claims_audit.md` (M4); M6 re-check in `evidence_audit.md` section 7 (`m4_audit.py`: integrity and raw checks true, 0 unmatched numbers; X-002, X-003, X-004, X-008 checked against full texts).
- [ ] Owner review complete (author_review.md)
- [ ] Owner approval for any push, release or publication (G-PUBLIC)

## Version and date at the release (B8)

Owner, 2026-11-26, decision sheet B8: `CITATION.cff` keeps `version: "0.1.0-rc1"` and no `date-released` until the release. At the release the version becomes `0.1.0` and `date-released` is set to the release day. `pyproject.toml` stays at `0.0.0` (changing it would change `uv.lock` and the recorded environments).

## Release notes (draft)

- Venue: GitHub release only (owner, 2026-11-26, decision sheet R-MARKET-1), with the committed PDFs attached (B10).
- External build and check tools are used but not redistributed: pandoc (GPL-2.0-or-later) converts Markdown to Typst and LaTeX, Google Chrome (proprietary) runs the demo accessibility check, and MPL-2.0 lightningcss is a build-time dependency of the demo toolchain, as listed in `dependency_licences.md` (B13).
- Sources not read in full are labelled as such (abstract record read, or the sections checked) in the manuscript references and `research/literature_review.md`; the owner accepted the labels (B14).


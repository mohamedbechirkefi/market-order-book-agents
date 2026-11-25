<!-- SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0 -->
# Release checklist (M6). Nothing is checked at M0.

**Status (2026-11-25):** release candidate prepared in M6 and awaiting the owner's review and G-PUBLIC decision. Each ticked item was verified by the AI assistant in this session; the evidence is next to it. The two owner items stay unticked.

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

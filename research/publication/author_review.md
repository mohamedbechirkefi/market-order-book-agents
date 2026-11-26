<!-- SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0 -->
# Owner review checklist (M6). Not started at M0.

- [ ] Authorship and affiliation metadata approved by the owner (no affiliation by default)
- [ ] AI assistance disclosure accurate (role of the AI, human verification performed)
- [ ] Protocol freeze approvals recorded for every confirmatory experiment
- [ ] Claims and limitations reviewed
- [ ] Licence wording (custom non-commercial, not open source) correct everywhere
- [ ] Publication venue, eligibility and fees checked (paid venues out of scope)

All six boxes above are unticked. No agent had ticked any of them (checked in M5 and again in M6, 2026-11-25); only the owner signs this checklist off.

## Prepared for the owner (M6, 2026-11-25)

The release candidate is prepared, not released (owner, 2026-11-25, "Next" (second), `labs/_shared/owner-approvals-2026-11-25e.md`). Suggested reading for each box:

| Box | What to read |
| --- | --- |
| Authorship and affiliation | `research/paper/manuscript.md` front matter (author line) and the status paragraph under it; `CITATION.cff` (`authors`, `title`, `version`); `README.md` section "Citation"; decision log D-001 and the owner-approvals record C3 cited there. |
| AI assistance disclosure | `research/paper/manuscript.md` section 11 (approved wording, D-017); `research/publication/review_pass_2.md` (what the AI's internal review did); `CLAUDE.md` (division of roles). |
| Protocol freeze approvals | `research/freeze.json` (hashes and the `deviations` list DEV-1 to DEV-4); decision log D-010, D-011, D-014, D-015; `research/experiment_registry.csv`. |
| Claims and limitations | `research/paper/manuscript.md` abstract, sections 5 to 9; `research/claims_register.csv` (C-001 to C-021, X-001 to X-008); `research/limitations.md`; `research/publication/evidence_audit.md` (sections 5 and 7); the PDFs `research/paper/manuscript.pdf` (20 pages), `supplementary.pdf` (3) and `research/experiments/EXP-00N/report.pdf` (8, 7, 5, 5, 5). |
| Licence wording | `README.md` section "Licence"; `CITATION.cff` header comments; the SPDX header of each file; `research/publication/dependency_licences.md` (two external tools flagged). |
| Publication venue, eligibility and fees | Nothing chosen. `master_prompt.md` section 11.7 (GitHub release as the zero-cost baseline; DOI or preprint hosting optional and owner-approved). |

### Open decisions for the owner (each one sentence)

1. Whether to push, tag, release or publish anything is the owner's decision under G-PUBLIC; M6 did none of these.
2. The repository and demo public URL is an owner-only fact and stays a placeholder until the owner publishes.
3. The owner confirms that there is no funding and no competing interest, or supplies them, before any release (manuscript section 11).
4. The owner confirms the author line and the absence of an affiliation as printed (approved as C3; listed again because it is an owner-only fact).
5. `CITATION.cff` now carries the manuscript title and version `0.1.0-rc1` with no `date-released`; the owner accepts or changes the version label and re-adds `date-released` at publication (owner-approvals-2026-11-25e, coordinator default).
6. The owner reads the manuscript in full (README: "Full-text owner review of the manuscript is pending") and ticks the six boxes above, or returns corrections.
7. The owner decides whether the release notes name the two flagged external tools, pandoc (GPL-2.0-or-later) and Google Chrome (proprietary), which build or check outputs but are not distributed.
8. The owner decides whether the committed PDFs are part of the release or are rebuilt at release time with `scripts/build_pdfs.py` (they are byte-reproducible from the sources).
9. The owner chooses a publication venue, if any, under the zero-cost rule (paid venues out of scope).

### Remaining owner placeholders (file and line, updated 2026-11-26)

The repository URL, demo URL, funding and competing-interest placeholders listed on 2026-11-25 were filled on 2026-11-26 (owner, 2026-11-26, decision sheet B1, B2, B4; decision D-021). One placeholder remains:

- `articles/medium.md` line 18: figure placeholder for the demo screenshot (`docs/demo.png` exists); it belongs to the owner's article review (B15).

## Owner answers recorded (2026-11-26)

Source: owner, 2026-11-26, decision sheet (`labs/_shared/owner-decision-sheet-2026-11-26.md`; answers in `labs/_shared/owner-approvals-2026-11-26.md`). Applied in decision D-021. No box above is ticked by this record.

| Id | Answer | Applied here |
| --- | --- | --- |
| A1 | Every repository is public since 2026-11-25. | Out-of-date "not published" statements corrected in editable files; append-only records unchanged. |
| B1 | Repository URL `https://github.com/mohamedbechirkefi/market-order-book-agents`. | README, `CITATION.cff` (`repository-code`), manuscript section 10, articles, demo README and footer. |
| B2 | Demo on Cloudflare Workers, free plan, `https://market-order-book-agents.kefimohamedbechir.workers.dev`, deployed by the coordinator. | URLs filled; `demo/wrangler.jsonc` (assets only, `./dist`). Not deployed from this repository. |
| B3 | "Mohamed Bechir Kefi, independent researcher". | Manuscript, supplement, five reports, articles, README, page footer; `CITATION.cff` affiliation "Independent researcher". |
| B4 | No funding; no competing interests. | Manuscript section 11 and README. |
| B6, B7 | Title approved; CITATION.cff carries the manuscript title. | Already the case. |
| B8 | `0.1.0-rc1` now; `0.1.0` and `date-released` at the release; `pyproject.toml` stays `0.0.0`. | Recorded in `release_checklist.md`. |
| B9 | Scrub home paths from editable files. | `CLAUDE.md`, `src/market/report.py`; 8 lines in 6 files remain, with reasons (`reproducibility_report.md` section 7). |
| B10, B13 | PDFs kept and attached to the release; build-tool licence sentence. | `release_checklist.md` "Release notes (draft)". |
| B14 | Source-level labels accepted. | Recorded; no text change needed. |
| R-MARKET-1 | Publication venue: GitHub release only. | Recorded in `release_checklist.md`. |

Answers 1 to 5 and 7 to 9 of the "Open decisions" list above are settled by these answers (push already done by the coordinator; URLs filled; funding and competing interests stated; author line confirmed; version rule recorded; tools named in the release notes; PDFs kept; venue chosen).

**Still open (owner only):** B15, the article drafts and their titles (`articles/medium.md`, `articles/linkedin.md`); B16, the full-text review of the manuscript and the sign-off of the six boxes above; B18, the GitHub release, tag and any DOI or preprint. No protocol freeze is pending in this repository.

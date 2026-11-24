<!-- SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0 -->
# Release checklist (M6). Nothing is checked at M0.

- [ ] Clean clone into a separate directory; `uv sync --frozen` succeeds (output recorded)
- [ ] Full test suite run; actual counts recorded in progress.md
- [ ] Smoke reproduction matches committed summary within documented tolerance
- [ ] Demo builds and works offline after load
- [ ] data/manifest.json and artifact_manifest.json verified; all links resolve
- [ ] Secret and personal-identifier scan clean
- [ ] Licence headers present; third-party licences recorded
- [ ] Manuscript and report PDFs compiled (pandoc to Typst) and visually inspected
- [ ] Claims audit complete (claims_audit.md)
- [ ] Owner review complete (author_review.md)
- [ ] Owner approval for any push, release or publication (G-PUBLIC)

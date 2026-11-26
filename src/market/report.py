# SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0
"""Report generator: tables and figures built only from validated run-result files.

Outputs (in the results folder): ``tables/arm_summary.csv``, ``tables/paired_contrasts.csv``,
``figures/*.svg`` and ``summary.md``; optionally ``summary.pdf`` through pandoc to Typst
(``-V mainfont="Libertinus Serif"``, the M0 workaround) and the ``typst`` Python package.
Exploratory inputs are labelled exploratory in every output.
"""

from __future__ import annotations

import csv
import json
import os
import re
import subprocess
from html import escape
from pathlib import Path

import numpy as np

from .analysis import bootstrap_mean_ci, d_z, paired_differences
from .runner import load_results

SUMMARY_METRICS = ("vci", "realised_volatility", "excess_kurtosis", "return_acf1", "mean_spread",
                   "mean_depth_at_best", "volume_per_step", "max_drawdown", "one_sided_fraction", "rejected_fraction")
CONTRAST_METRICS = ("vci", "vci_dt10", "vci_dt200", "realised_volatility", "mean_spread", "max_drawdown")

# Default tool locations: the shared toolchain folder `.tools/` next to this repository
# (`../.tools/` from the repository root); overridable by MARKET_PANDOC and MARKET_TYPST_PYTHON.
_SHARED_TOOLS = Path(__file__).resolve().parents[3] / ".tools"
DEFAULT_PANDOC = str(_SHARED_TOOLS / "pandoc")
DEFAULT_TYPST_PY = str(_SHARED_TOOLS / "py" / "bin" / "python")

# Typst rules added before the pandoc template (M6 visual inspection): no creation date, so that
# a rebuild of unchanged sources gives identical PDF bytes; tables in a smaller size, left
# aligned and not justified, so that wide tables stay readable; figures and tables may break across
# pages, so that a caption is not separated from its table; centred blocks (the title, figures) are
# not justified; code-formatted formulas wrap; long metric names in tables may break after an underscore.
TYPST_PREAMBLE = "\n".join([
    "#set document(date: none)",
    "#show table: set text(size: 8pt)",
    "#show table: set align(left)",
    "#show table: set par(justify: false)",
    r'#show table: it => { show "_": "_\u{200B}"; it }',
    "#show figure: set block(breakable: true)",
    "#show align: set par(justify: false)",
    "#show raw: set text(size: 0.9em)",
])


def _by_arm(docs: list[dict]) -> dict[str, list[dict]]:
    arms: dict[str, list[dict]] = {}
    for d in docs:
        arms.setdefault(d["arm"], []).append(d)
    for v in arms.values():
        v.sort(key=lambda d: d["seed"])
    return dict(sorted(arms.items()))


def _fmt(x, nd=4) -> str:
    if x is None:
        return "n/a"
    if isinstance(x, (int, np.integer)):
        return str(int(x))
    return f"{x:.{nd}g}"


def arm_summary(docs: list[dict]) -> list[dict]:
    rows = []
    for arm, ds in _by_arm(docs).items():
        ok = [d for d in ds if d["status"] == "ok"]
        row = {"arm": arm, "runs": len(ds), "failed": len(ds) - len(ok),
               "degenerate": sum(d["flags"]["degenerate"] for d in ok),
               "runtime_mean_s": float(np.mean([d["runtime_s"] for d in ds]))}
        for m in SUMMARY_METRICS:
            vals = [d["metrics"].get(m) for d in ok if d["metrics"].get(m) is not None]
            row[f"{m}_n"] = len(vals)
            row[f"{m}_mean"] = float(np.mean(vals)) if vals else None
            row[f"{m}_sd"] = float(np.std(vals, ddof=1)) if len(vals) >= 2 else None
        rows.append(row)
    return rows


def paired_contrasts(docs: list[dict], control: str, metrics=CONTRAST_METRICS, n_resamples: int = 10_000,
                     exclude: tuple[str, ...] = ()) -> list[dict]:
    """Paired contrasts of every arm against ``control``; arms in ``exclude`` are left out (protocol amendment A1)."""
    arms = {a: v for a, v in _by_arm(docs).items() if a not in exclude}
    if control not in arms:
        raise ValueError(f"control arm {control!r} not in results (arms: {sorted(arms)})")
    def per_seed(arm, m):
        return {d["seed"]: d["metrics"].get(m) for d in arms[arm] if d["status"] == "ok"}
    rows = []
    for arm in arms:
        if arm == control:
            continue
        for m in metrics:
            diffs = paired_differences(per_seed(arm, m), per_seed(control, m))
            x = np.array(list(diffs.values()))
            row = {"treatment": arm, "control": control, "metric": m, "n_pairs": len(x),
                   "mean_diff": float(x.mean()) if len(x) else None,
                   "sd_diff": float(np.std(x, ddof=1)) if len(x) >= 2 else None,
                   "d_z": d_z(x) if len(x) >= 2 else None, "ci95_low": None, "ci95_high": None}
            if len(x) >= 2:
                row["ci95_low"], row["ci95_high"] = bootstrap_mean_ci(x, n_resamples=n_resamples)
            rows.append(row)
    return rows


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = list(rows[0].keys()) if rows else []
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if v is None else v) for k, v in r.items()})


# ----- SVG figures (no plotting dependency) -----
_W, _H, _ML, _MR, _MT, _MB = 640, 360, 70, 20, 40, 50


def _axis_svg(title: str, ylab: str, ymin: float, ymax: float, xlabels: list[str] | None, desc: str) -> list[str]:
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{_W}" height="{_H}" viewBox="0 0 {_W} {_H}" role="img" aria-labelledby="t d">',
         f'<title id="t">{escape(title)}</title><desc id="d">{escape(desc)}</desc>',
         f'<rect width="{_W}" height="{_H}" fill="#ffffff"/>',
         f'<text x="{_W/2}" y="22" font-family="serif" font-size="15" text-anchor="middle" fill="#111">{escape(title)}</text>']
    x0, x1, y0, y1 = _ML, _W - _MR, _H - _MB, _MT
    s.append(f'<line x1="{x0}" y1="{y0}" x2="{x1}" y2="{y0}" stroke="#333"/><line x1="{x0}" y1="{y0}" x2="{x0}" y2="{y1}" stroke="#333"/>')
    for k in range(5):
        v = ymin + (ymax - ymin) * k / 4
        y = y0 - (y0 - y1) * k / 4
        s.append(f'<line x1="{x0-4}" y1="{y:.1f}" x2="{x1}" y2="{y:.1f}" stroke="#ddd"/>'
                 f'<text x="{x0-6}" y="{y+4:.1f}" font-family="sans-serif" font-size="11" text-anchor="end" fill="#333">{v:.3g}</text>')
    s.append(f'<text x="16" y="{(y0+y1)/2}" font-family="sans-serif" font-size="12" text-anchor="middle" fill="#333" transform="rotate(-90 16 {(y0+y1)/2})">{escape(ylab)}</text>')
    if xlabels:
        n = len(xlabels)
        for i, lab in enumerate(xlabels):
            x = x0 + (x1 - x0) * (i + 0.5) / n
            s.append(f'<text x="{x:.1f}" y="{y0+18}" font-family="sans-serif" font-size="12" text-anchor="middle" fill="#333">{escape(lab)}</text>')
    return s


def _scale(v, lo, hi):
    y0, y1 = _H - _MB, _MT
    return y0 - (y0 - y1) * ((v - lo) / (hi - lo) if hi > lo else 0.5)


def strip_plot(path: Path, by_arm: dict[str, list[float]], title: str, ylab: str, desc: str) -> None:
    allv = [v for vs in by_arm.values() for v in vs]
    lo, hi = (min(allv), max(allv)) if allv else (0.0, 1.0)
    pad = (hi - lo) * 0.08 or 0.01
    lo, hi = lo - pad, hi + pad
    labels = list(by_arm)
    s = _axis_svg(title, ylab, lo, hi, labels, desc)
    n = len(labels)
    x0, x1 = _ML, _W - _MR
    for i, lab in enumerate(labels):
        vs = by_arm[lab]
        xc = x0 + (x1 - x0) * (i + 0.5) / n
        for j, v in enumerate(vs):
            jitter = ((j * 37) % 21 - 10) * 1.6
            s.append(f'<circle cx="{xc+jitter:.1f}" cy="{_scale(v, lo, hi):.1f}" r="3.2" fill="#1f4e79" fill-opacity="0.65"/>')
        if vs:
            ym = _scale(float(np.mean(vs)), lo, hi)
            s.append(f'<line x1="{xc-22:.1f}" y1="{ym:.1f}" x2="{xc+22:.1f}" y2="{ym:.1f}" stroke="#b22222" stroke-width="2"/>')
    s.append("</svg>")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(s) + "\n", encoding="utf-8")


def line_plot(path: Path, series: dict[str, list[float]], title: str, ylab: str, desc: str) -> None:
    allv = [v for vs in series.values() for v in vs]
    lo, hi = min(allv), max(allv)
    pad = (hi - lo) * 0.05 or 1.0
    lo, hi = lo - pad, hi + pad
    s = _axis_svg(title, ylab, lo, hi, None, desc)
    colors = ["#1f4e79", "#b22222", "#2e7d32", "#6a1b9a", "#ef6c00", "#455a64"]
    x0, x1 = _ML, _W - _MR
    for k, (lab, vs) in enumerate(series.items()):
        if len(vs) < 2:
            continue
        pts = " ".join(f"{x0 + (x1 - x0) * i / (len(vs) - 1):.1f},{_scale(v, lo, hi):.1f}" for i, v in enumerate(vs))
        c = colors[k % len(colors)]
        s.append(f'<polyline points="{pts}" fill="none" stroke="{c}" stroke-width="1.2"/>')
        s.append(f'<text x="{x1-4}" y="{_MT + 14 + 14*k}" font-family="sans-serif" font-size="11" text-anchor="end" fill="{c}">{escape(lab)}</text>')
    s.append(f'<text x="{(x0+x1)/2}" y="{_H-12}" font-family="sans-serif" font-size="12" text-anchor="middle" fill="#333">event time (steps, full run including burn-in)</text>')
    s.append("</svg>")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(s) + "\n", encoding="utf-8")


def build_report(results_dir: Path, control: str | None = None, pdf: bool = False, n_resamples: int = 10_000,
                 exclude: tuple[str, ...] = ()) -> dict:
    results_dir = Path(results_dir)
    docs = load_results(results_dir)
    labels = {d["label"] for d in docs}
    label = "confirmatory" if labels == {"confirmatory"} else "exploratory"
    arms = _by_arm(docs)
    control = control or ("A0" if "A0" in arms else next(iter(arms)))
    summ = arm_summary(docs)
    if control in exclude:
        raise ValueError(f"control arm {control!r} is excluded from contrasts")
    contr = paired_contrasts(docs, control, n_resamples=n_resamples, exclude=exclude) if len(arms) > 1 else []
    _write_csv(results_dir / "tables" / "arm_summary.csv", summ)
    if contr:
        _write_csv(results_dir / "tables" / "paired_contrasts.csv", contr)
    seeds = sorted({d["seed"] for d in docs})
    tag = "EXPLORATORY, not evidence for any hypothesis" if label == "exploratory" else "confirmatory"
    vci_by_arm = {a: [d["metrics"]["vci"] for d in ds if d["status"] == "ok" and d["metrics"]["vci"] is not None] for a, ds in arms.items()}
    strip_plot(results_dir / "figures" / "vci_by_arm.svg", vci_by_arm, f"VCI per run by arm ({tag})", "VCI (dimensionless)",
               f"Strip plot of the volatility clustering index, one dot per seed (n = {len(seeds)} seeds per arm), red bar = arm mean.")
    rt_by_arm = {a: [d["runtime_s"] for d in ds] for a, ds in arms.items()}
    strip_plot(results_dir / "figures" / "runtime_by_arm.svg", rt_by_arm, f"Runtime per run by arm ({tag})", "seconds",
               "Wall-clock runtime per run, one dot per seed, red bar = arm mean.")
    if contr:
        diffs = {}
        for arm in arms:
            if arm == control or arm in exclude:
                continue
            per_t = {d["seed"]: d["metrics"]["vci"] for d in arms[arm] if d["status"] == "ok"}
            per_c = {d["seed"]: d["metrics"]["vci"] for d in arms[control] if d["status"] == "ok"}
            diffs[f"{arm}-{control}"] = list(paired_differences(per_t, per_c).values())
        strip_plot(results_dir / "figures" / "vci_paired_diff.svg", diffs, f"Paired VCI difference vs {control} ({tag})",
                   "VCI difference", "One dot per seed: VCI(treatment, seed) minus VCI(control, seed); red bar = mean difference.")
    series_files = sorted((results_dir / "series").glob("*.json")) if (results_dir / "series").exists() else []
    if series_files:
        ser = {}
        for p in series_files:
            j = json.loads(p.read_text(encoding="utf-8"))
            ser[j["run_id"]] = j["mid"]
        line_plot(results_dir / "figures" / "mid_paths.svg", ser, f"Mid-price paths, first seed per arm ({tag})", "mid price (price units)",
                  "Mid price sampled at fixed step intervals for the first seed of each arm.")

    md = [f"<!-- SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0 -->",
          f"# Results summary: {docs[0]['exp_id']} ({label.upper()})", ""]
    if label == "exploratory":
        md += ["**Exploratory output on development seeds. Not a finding, not evidence for or against any hypothesis, "
               "and never to be quoted as a result.** It exists to measure runtime, seed spread and degenerate cases before the owner freezes the protocol.", ""]
    md += [f"Generated by `market.report` from {len(docs)} validated run files in `{results_dir.name}/runs/`. "
           f"Seeds: {seeds[0]}..{seeds[-1]} ({len(seeds)}). Arms: {', '.join(arms)}. Control for contrasts: {control}.", "",
           "## Arm summary (mean and SD over seeds)", "",
           "| Arm | Runs | Failed | Degenerate | Runtime mean (s) | VCI | Realised vol. | Mean spread (price units) | Max drawdown | One-sided frac. | Rejected frac. |",
           "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for r in summ:
        def ms(m):
            return f"{_fmt(r[m + '_mean'])} ({_fmt(r[m + '_sd'])})"
        md.append(f"| {r['arm']} | {r['runs']} | {r['failed']} | {r['degenerate']} | {r['runtime_mean_s']:.3f} | {ms('vci')} | "
                  f"{ms('realised_volatility')} | {ms('mean_spread')} | {ms('max_drawdown')} | {ms('one_sided_fraction')} | {ms('rejected_fraction')} |")
    if exclude:
        md += ["", f"Arms reported but excluded from every contrast (pre-declared, protocol amendment A1): {', '.join(exclude)}."]
    if contr:
        md += ["", f"## Paired contrasts against {control} (mean over seeds of treatment minus control)", "",
               "Percentile bootstrap 95% interval over seeds (10,000 resamples, seed 20261124); d_z = mean / SD of paired differences.", "",
               "| Treatment | Metric | Pairs | Mean diff. | SD diff. | d_z | 95% interval |", "| --- | --- | --- | --- | --- | --- | --- |"]
        for r in contr:
            md.append(f"| {r['treatment']} | {r['metric']} | {r['n_pairs']} | {_fmt(r['mean_diff'])} | {_fmt(r['sd_diff'])} | {_fmt(r['d_z'], 3)} | "
                      f"[{_fmt(r['ci95_low'])}, {_fmt(r['ci95_high'])}] |")
    md += ["", "## Figures", "",
           "![Volatility clustering index per run, one dot per seed; the red bar is the arm mean (dimensionless).](figures/vci_by_arm.svg)", ""]
    if contr:
        md += [f"![Paired VCI differences against {control}, one dot per seed; the red bar is the mean difference.](figures/vci_paired_diff.svg)", ""]
    if series_files:
        md += ["![Mid-price path of the first seed of each arm (price units against event time).](figures/mid_paths.svg)", ""]
    md += ["![Wall-clock runtime per run in seconds, one dot per seed.](figures/runtime_by_arm.svg)", ""]
    (results_dir / "summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    out = {"label": label, "runs": len(docs), "arms": list(arms), "control": control, "excluded_from_contrasts": list(exclude), "summary": str(results_dir / "summary.md"), "pdf": None}
    if pdf:
        out["pdf"] = str(render_pdf(results_dir / "summary.md"))
    return out


def _first_heading(text: str) -> tuple[str | None, str]:
    """Return the first level-1 Markdown heading and the text without it (None if absent)."""
    lines = text.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if line.startswith("# "):
            return line[2:].strip(), "".join(lines[:i] + lines[i + 1:])
    return None, text


def render_pdf(md_path: Path, bibliography: Path | None = None, keep_typ: bool = False) -> Path:
    """Markdown to PDF through pandoc (Typst writer) and the typst Python package.

    SVG figures are embedded by Typst. Tool paths are overridable by MARKET_PANDOC and
    MARKET_TYPST_PYTHON. Raises RuntimeError when the toolchain is unavailable.

    When the Markdown has no YAML ``title``, its first level-1 heading becomes the document
    title (PDF metadata and title block) and is removed from the body, so it is not printed
    twice. With ``bibliography``, pandoc resolves ``[@key]`` citations (author-date) and the
    generated list is suppressed, because the documents carry their own annotated reference
    list. Pages are numbered; ``TYPST_PREAMBLE`` sets the table and figure rules, and figure
    numbering is turned off when the captions already carry "Figure N.". With ``keep_typ`` the
    intermediate ``.typ`` file is kept for inspection (for example rendering pages to PNG);
    otherwise it is deleted.
    """
    md_path = Path(md_path).resolve()
    pandoc = os.environ.get("MARKET_PANDOC", DEFAULT_PANDOC)
    typst_py = os.environ.get("MARKET_TYPST_PYTHON", DEFAULT_TYPST_PY)
    typ = md_path.with_suffix(".typ")
    pdf = md_path.with_suffix(".pdf")
    text = md_path.read_text(encoding="utf-8")
    args = [pandoc, "-f", "markdown", "-s", "-t", "typst-citations", "-V", "mainfont=Libertinus Serif", "-V", "page-numbering=1",
            "-V", "papersize=a4", "--columns=1000", "-o", str(typ)]
    if not text.startswith("---"):
        title, text = _first_heading(text)
        if title:
            args += ["-M", f"title={title}"]
    preamble = TYPST_PREAMBLE
    if re.search(r"!\[Figure \d", text):
        # the captions carry their own "Figure N." label; Typst's automatic number would repeat it
        preamble += "\n#set figure(numbering: none)"
    args += ["-V", f"header-includes={preamble}"]
    if bibliography is not None:
        args += ["--citeproc", "--bibliography", str(Path(bibliography).resolve()), "-M", "suppress-bibliography=true"]
    try:
        subprocess.run(args, input=text, check=True, capture_output=True, text=True, cwd=md_path.parent)
        code = "import sys, typst; typst.compile(sys.argv[1], output=sys.argv[2], root=sys.argv[3])"
        subprocess.run([typst_py, "-I", "-c", code, str(typ), str(pdf), str(md_path.parent)],
                       check=True, capture_output=True, text=True, cwd=md_path.parent)
    except FileNotFoundError as e:
        raise RuntimeError(f"PDF toolchain unavailable: {e}") from e
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"PDF build failed: {e.stderr.strip()[:500]}") from e
    finally:
        if typ.exists() and not keep_typ:
            typ.unlink()
    return pdf

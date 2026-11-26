<!-- SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0 -->
# MARKET demo: design plan (owner request, 2026-11-26)

## Subject, audience, job

- **Subject.** A preregistered simulation of a limit-order book: do trend followers raise volatility clustering? The frozen verdict is "invalidated" because the sign of the effect depends on the sampling interval.
- **Audience.** A curious technical reader, an admissions committee skimming for rigour, a researcher checking the numbers.
- **Primary job.** State the question and the frozen answer in one breath, show the sign reversal across horizons as the study's own picture, then let the visitor run the order book.

## Direction: the quote board and the tape

A 1980s trading floor seen through two of its objects: the **quote board** (a deep green field with amber figures, the board above the Chicago pits) and the **ticker tape** (a pale paper strip with printed marks). The page is the tape: a cool, slightly green paper. The board appears once, as the hero, and again as the frame of the sandbox, where the visitor trades in the pit. Bids are a floor-jacket blue, asks a signal red; they never carry any other meaning.

## Colour (6 named values)

| Name | Hex | Role |
|---|---|---|
| Board green | `#0E2B23` | hero field, sandbox frame, primary button |
| Tape paper | `#ECEFE7` | page background (cool grey-green, not cream) |
| Ink | `#18221E` | body text, rules, estimate ticks |
| Ticker amber | `#F0B43C` | figures and headline on the board only (never on paper) |
| Bid blue | `#1C56A0` | bids, confidence intervals, links |
| Ask red | `#B4261F` | asks, the sell shock |

Support colours are tints of these (muted ink `#4A5650`, tape rule `#C5CCC2`, raised paper `#F6F7F2`). Light only: the board already gives the page its dark moment, and a dark tape would lose the paper metaphor. `color-scheme: light` keeps form controls consistent.

## Type

- **Big Shoulders Display** (variable, OFL-1.1): display face. Condensed, built from the signage of Chicago, the city of the futures pits. Used large and tight for the headline, the verdict word and section titles; never for body text.
- **Libre Franklin** (variable, OFL-1.1): text and figures. A revival of Franklin Gothic, the face of the newspaper stock tables. Tabular figures for every number; no monospace face anywhere.

Scale (rem): 0.8125 / 0.9375 / 1.0625 body / 1.375 / 2 / 3.25 / clamp(2.75, 7vw, 5.5) hero. Body 1.0625rem at 1.6 leading, measure 68ch.

## Layout

```
+--------------------------------------------------------------+
| [M] MARKET   Answer  Evidence  Experiments  Sandbox  Method  |  sticky tape bar, sliding underline
+--------------------------------------------------------------+
| BOARD GREEN                                                  |
|  Do trend followers raise volatility        +-------------+ |
|  clustering in a simulated order book?      | depth ladder| |
|  Answer under the frozen rule: INVALIDATED  | asks / bids | |
|  one sentence of why                        +-------------+ |
|  ====== ticker tape strip: clustered print marks ========== |
|  "Illustration, not study data"                              |
+--------------------------------------------------------------+
| TAPE PAPER                                                   |
|  The answer depends on the horizon   [horizon board: 4 rows] |
|  placebo board                                               |
|  Every registered experiment: ledger rows, not cards         |
|  Price paths: four small multiples                           |
|  Exploratory grid (dashed board)                             |
| BOARD GREEN frame: the pit (sandbox)                         |
|  Assumptions, method, limitations, sources                   |
| footer: links, licence, AI use, font credits                 |
+--------------------------------------------------------------+
```

Left-aligned throughout; the hero splits 7/5 on wide screens and stacks on phones (ladder under the text, tape full bleed).

## Motion

- **Hero moment (once, about 2.4 s).** The tape prints: marks appear right to left in bursts, tall marks bunching together and quiet stretches between them, which is what volatility clustering looks like on a tape. The depth ladder beside the headline fills from the spread outward (bars scale in from the middle, 40 ms stagger). Labelled "Illustration, not study data"; it shows no number.
- **Answers to actions.** The nav underline slides to the section in view (transform only). Interval charts draw once when scrolled into view: each interval grows out of its estimate tick (scaleX, 420 ms, strong ease-out, 50 ms stagger). Run button press scale 0.97; while the worker runs, the progress bar fills; the result panel enters with `@starting-style` (opacity and an 8 px rise, 260 ms). Scrubbing the order-book step is not animated (it fires tens of times).
- **Reduced motion.** No hero animation (the tape and ladder render in their final state), charts appear without growth, the panel only fades. Hover lift only inside `(hover: hover) and (pointer: fine)`. No `transition: all`.

## The one memorable thing

The ticker tape across the foot of the hero, printing in clustered bursts. Everything else stays disciplined so the tape is what a visitor remembers.

## Review against the frontend-design tells and the other demos

- *First draft* had a near-black hero with a single amber accent. That is tell 2 (near-black plus one bright accent). **Changed** to a saturated board green field, which is the actual colour of the period quote boards, with amber as figure colour and the bid/ask pair on paper.
- *First draft* used a monospace face for prices on the tape and the ladder. Tell 5. **Changed** to Libre Franklin tabular figures, which is also more faithful to printed stock tables.
- *First draft* put each experiment in a rounded card. Tell 4. **Changed** to ledger rows on the tape with a left rule, no shadows; only the sandbox has a frame, because it is a different thing (your run).
- *Labels.* The old page used upper-case tracked tags everywhere. **Changed** to sentence-case labels with distinct rule styles (solid, dashed, dotted, double) so status is not told by colour alone; no eyebrow above every heading.
- *Against the other demos.* FARE owns the split-flap departure board (dark, flipping digits), so MARKET avoids flip digits and dark full pages; SCALE owns blueprint blue; PULSE owns the control room. MARKET is the only one with a green board and a printed paper tape.

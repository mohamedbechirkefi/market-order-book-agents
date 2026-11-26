<!-- SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0 -->
<!-- DRAFT for the owner. Not published. Numbers copied from research/paper/manuscript.md; tests/test_demo_export.py checks them. -->

I preregistered a small simulation study and the frozen verdict came back "invalidated". I think that is the useful part.

The question: in a simulated limit-order book, do trend-following traders raise volatility clustering compared with random-order traders?

What I built: a tested order-book simulator (price-time priority, cash and inventory accounting), five registered experiments, 480 confirmatory runs on 30 paired seeds, an aggressiveness-matched placebo arm, and a static page with an in-browser sandbox.

One defensible finding: at the preregistered sampling interval the trend-follower effect was -0.007825 (95% interval [-0.0268, 0.01785]), but it was positive at other intervals, so the frozen robustness rule declared the primary interpretation invalidated. Coin-flip agents trading just as aggressively raised clustering, and trend following added nothing beyond them at that interval.

Caveat: this is one simulated market under explicit assumptions, not a statement about real markets and not trading advice. Read with the sign of the hypothesis as reference, the same rule would say "qualified"; either way, the answer depends on the sampling interval.

Repository: https://github.com/mohamedbechirkefi/market-order-book-agents
Demo: https://market-order-book-agents.kefimohamedbechir.workers.dev

Mohamed Bechir Kefi, independent researcher. Independent preprint draft, not peer-reviewed. AI assistance (Claude, Anthropic) disclosed in the manuscript.

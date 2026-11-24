<!-- SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0 -->
# Literature and dataset review (M0, started 2026-11-24)

This is not a systematic review. Searches used the WebSearch tool; a source counts as **opened** only if its page was fetched with WebFetch in this session. "Opened" here means the abstract or bibliographic record page was read, not the full text, unless stated. Everything else is **unverified**.

## 1. Sources opened

| Key | Reference | Opened page (accessed 2026-11-24) | What was verified | Relevance |
| --- | --- | --- | --- | --- |
| GodeSunder1993 | D. K. Gode, S. Sunder. Allocative efficiency of markets with zero-intelligence traders: market as a partial substitute for individual rationality. *Journal of Political Economy* 101(1):119-137, 1993. DOI 10.1086/261868 | https://econpapers.repec.org/RePEc:ucp:jpolec:v:101:y:1993:i:1:p:119-37 | Bibliographic record and abstract: random bids and offers under a budget constraint reach near-full allocative efficiency in a double auction | Origin of the random-order ("zero-intelligence") trader as a baseline |
| Smith2003 | E. Smith, J. D. Farmer, L. Gillemot, S. Krishnamurthy. Statistical theory of the continuous double auction. arXiv cond-mat/0210475 (2002); *Quantitative Finance* 3(6):481-514, 2003. DOI 10.1088/1469-7688/3/6/307 | https://arxiv.org/abs/cond-mat/0210475 | Abstract: independent random order flow; predictions for volatility, spread, depth, price impact; order size matters more than tick size for most properties | Random-order CDA as null model; motivates the tick-size sensitivity |
| Farmer2005 | J. D. Farmer, P. Patelli, I. I. Zovko. The predictive power of zero intelligence in financial markets. arXiv cond-mat/0309233 (v2 2004); *PNAS* 102(11):2254-2259, 2005. DOI 10.1073/pnas.0409157102 | https://arxiv.org/abs/cond-mat/0309233 | Abstract: random order placement model tested on London Stock Exchange data for eleven stocks; one free parameter accounts for most spread variance | Strongest justification for the random-order baseline. Journal metadata verified from search result only (journal ref not shown on the arXiv page) |
| Chiarella2009 | C. Chiarella, G. Iori, J. Perello. The impact of heterogeneous trading rules on the limit order book and order flows. arXiv 0711.3581 (2007); *Journal of Economic Dynamics and Control* 33:525-537, 2009. DOI 10.1016/j.jedc.2008.08.001 | https://arxiv.org/abs/0711.3581 | Abstract and journal ref: fundamentalist, chartist and noise components; chartist component reported as mainly responsible for fat tails and clustering | Direct motivation of the directional H1 |
| LuxMarchesi1999 | T. Lux, M. Marchesi. Scaling and criticality in a stochastic multi-agent model of a financial market. *Nature* 397:498-500, 1999. DOI 10.1038/17290 | https://ideas.repec.org/a/nat/nature/v397y1999i6719d10.1038_17290.html | Bibliographic record and abstract: scaling attributed to interactions among participants rather than to news | Competing heterogeneous-agent tradition (not order-book based) |
| Cont2001 | R. Cont. Empirical properties of asset returns: stylized facts and statistical issues. *Quantitative Finance* 1(2):223-236, 2001. DOI 10.1080/713665670 | https://ideas.repec.org/a/taf/quantf/v1y2001i2p223-236.html | Bibliographic record and abstract: catalogue of stylized facts including dependence properties | Defines volatility clustering as a target pattern; full text not read (paywalled) |
| RatliffCrain2023 | E. Ratliff-Crain, C. M. Van Oort, J. Bagrow, M. T. K. Koehler, B. F. Tivnan. Revisiting Cont's stylized facts for modern stock markets. arXiv 2311.07738 (v2 2024) | https://arxiv.org/abs/2311.07738 | Abstract: eight of eleven facts supported on Dow 30 intraday data, Oct 2018 to Mar 2019 | Caution that stylized facts are not universal |
| Chakraborti2011 | A. Chakraborti, I. Muni Toke, M. Patriarca, F. Abergel. Econophysics: empirical facts and agent-based models. arXiv 0909.1974; *Quantitative Finance* 11:991-1012 and 1013-1041, 2011 | https://arxiv.org/abs/0909.1974 | Abstract and journal ref | Review of order-driven agent-based models |
| Byrd2019 | D. Byrd, M. Hybinette, T. Hybinette Balch. ABIDES: towards high-fidelity market simulation for AI research. arXiv 1904.12066, 2019 | https://arxiv.org/abs/1904.12066 ; licence at https://raw.githubusercontent.com/abides-sim/abides/master/LICENSE.txt | Abstract; code licence BSD 3-Clause (Copyright 2019 Georgia Tech Research Corporation) | Existing large simulator; this project does not use or copy its code |

## 2. Unverified (seen in search results only, not opened)

- LiCalzi, Milone and Pellizzari, replication showing Gode and Sunder's result depends on the market protocol (University of Venice working paper; URL seen: unive.it working paper 2008wp168). Unverified.
- Daniels, Farmer, Gillemot, Iori and Smith, earlier Poisson order-flow model (arXiv cond-mat/0112422). Unverified.
- ABIDES-Gym, arXiv 2110.14771. Unverified.
- A 2025 *Quantitative Finance* paper on Cont's facts was mentioned in a search summary without a checked reference. Unverified; not to be cited.

## 3. Candidate datasets

The registered experiments need no external data. Datasets were examined only as possible later comparison targets.

| Dataset | Source opened | Licence | Redistribution | Decision |
| --- | --- | --- | --- | --- |
| FI-2010 benchmark LOB dataset (Ntakaris, Magris, Kanniainen, Gabbouj and Iosifidis; NASDAQ Nordic Helsinki, 5 stocks, 10 days, June 2010) | https://research.fi/en/results/dataset/73eb48d7-4dbc-4a10-a52a-da745b47a649 (2026-11-24); Fairdata Metax record https://metax.fairdata.fi/rest/v2/datasets/73eb48d7-4dbc-4a10-a52a-da745b47a649 (opened 2026-11-24, access type "Open"); paper arXiv:1705.03233 v5 (PDF opened 2026-11-24), doi:10.1002/for.2543 | CC BY 4.0 (Metax record, licence URL https://creativecommons.org/licenses/by/4.0/); rights holder BigDataFinance | Allowed with attribution, including redistribution; not redistributed here because the archive is 1.86 GB | **Adopted 2026-11-24 (owner approval, round 2; D-009)** for the descriptive comparison EXP-005 only. The M0 objection (normalised features) is answered by the decimal-precision variant: dividing prices by a power of ten leaves log returns and relative spreads unchanged (checked in J-0004). Paper facts used: one representation per 10 consecutive events, 394,337 representations, trading 10:30 to 18:00, tick one cent |
| LOBSTER (NASDAQ TotalView-ITCH reconstructions) | https://vdc.univie.ac.at/data-access/lobster (2026-11-24); lobsterdata.com did not render | Not stated on the pages opened; access is institutional (account by request) | Unknown; presumed not redistributable | Excluded (no paid data, unclear rights). Blocker only if the owner wants real-data calibration |
| Synthetic data from this project's generator | n/a | Project licence (NOTICE.md) | Yes, regenerated from seeds | Primary data source |

No dataset bytes were downloaded in this session.

## 4. Gap and contribution (draft)

Random-order order books and chartist/fundamentalist order books are both well studied. The planned contribution is narrow: a small, tested, reproducible engine plus a paired, preregistered comparison that separates the trend-feedback effect on volatility clustering from the change in order aggressiveness (placebo arm). No novelty is claimed before a fuller literature search on placebo or aggressiveness-matched controls; this search was not done in M0 and is an M1 task.

<!-- SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0 -->
# Dependency licences (M6, 2026-11-25)

Collected on 2026-11-25 from the installed metadata: Python from `.venv` (`importlib.metadata`, field `License-Expression` or `License`, after `uv sync --frozen --all-groups --all-extras`), npm from `demo/node_modules/*/package.json` (field `license`) after `npm ci --prefer-offline`, and from `demo/package-lock.json` for optional platform packages that are not installed on this machine. Nothing here is a legal opinion; the owner checks the list before any release.

Accepted as permissive for this list: MIT, BSD (0BSD, 2-Clause, 3-Clause), ISC, Apache-2.0, PSF, MPL-2.0, Zlib, CC0-1.0.

## Python (`uv.lock`, Python 3.12)

| Package | Version | Licence | Role | Flag |
| --- | --- | --- | --- | --- |
| numpy | 2.5.4 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | runtime | none |
| hypothesis | 6.170.15 | MPL-2.0 | test (dev group) | none (file-level copyleft; used for tests only, not distributed) |
| pytest | 9.2.0 | MIT | test | none |
| iniconfig | 2.3.1 | MIT | test | none |
| pluggy | 1.7.0 | MIT | test | none |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause | test | none |
| Pygments | 2.21.0 | BSD-2-Clause | test | none |
| sortedcontainers | 2.4.0 | Apache 2.0 (metadata spelling) | test (hypothesis dependency) | none |
| hatchling | not installed | not checked (build backend, fetched only when a wheel is built) | build | unverified: no wheel was built in M6 |

## Build tools outside the lock files (shared toolchain, not distributed)

| Tool | Version | Licence | Role | Flag |
| --- | --- | --- | --- | --- |
| pandoc (binary) | 3.6.3 | GPL-2.0-or-later (pandoc's published licence; the binary prints only its copyright line) | Markdown to Typst and LaTeX conversion | **flag: copyleft.** Used as an external program; no pandoc code is copied or linked into this repository, and its output is not covered by its licence. |
| typst (Python package) | 0.15.0 | Apache-2.0 | PDF compilation | none |
| pypdf | 6.20.0 | BSD-3-Clause | PDF metadata check (M6) | none |
| uv | as in `labs/.tools/py` | not checked in M6 | installer | unverified |
| Node | 22.23.3 | not checked in M6 (Node's licence is MIT for its own code) | demo build | unverified |
| Google Chrome | system installation | proprietary | headless browser driven by `demo/tools/a11y_check.mjs` | **flag: proprietary.** Used as an external program for the accessibility check only; not distributed. |

## npm (`demo/package-lock.json`)

Direct dependencies: runtime `react` 19.3.1 and `react-dom` 19.3.1; development `@types/react` 19.3.0, `@types/react-dom` 19.3.0, `@vitejs/plugin-react` 6.1.2, `typescript` 5.9.3, `vite` 8.3.5, `vitest` 4.1.12. Only `react`, `react-dom` and `scheduler` reach the built page; everything else is a build or test tool.

| Package | Version | Licence | Role |
| --- | --- | --- | --- |
| @jridgewell/sourcemap-codec | 1.6.0 | MIT | dev |
| @oxc-project/types | 0.156.0 | MIT | dev |
| @rolldown/binding-darwin-arm64 | 1.2.19 | MIT | dev,optional |
| @rolldown/pluginutils | 1.1.1 | MIT | dev |
| @standard-schema/spec | 1.1.0 | MIT | dev |
| @types/chai | 5.2.3 | MIT | dev |
| @types/deep-eql | 4.0.2 | MIT | dev |
| @types/estree | 1.0.11 | MIT | dev |
| @types/react-dom | 19.3.0 | MIT | dev |
| @types/react | 19.3.0 | MIT | dev |
| @vitejs/plugin-react | 6.1.2 | MIT | dev |
| @vitest/expect | 4.1.12 | MIT | dev |
| @vitest/mocker | 4.1.12 | MIT | dev |
| @vitest/pretty-format | 4.1.12 | MIT | dev |
| @vitest/runner | 4.1.12 | MIT | dev |
| @vitest/snapshot | 4.1.12 | MIT | dev |
| @vitest/spy | 4.1.12 | MIT | dev |
| @vitest/utils | 4.1.12 | MIT | dev |
| assertion-error | 2.0.1 | MIT | dev |
| chai | 6.3.0 | MIT | dev |
| convert-source-map | 2.0.0 | MIT | dev |
| csstype | 3.2.4 | MIT | dev |
| detect-libc | 2.1.2 | Apache-2.0 | dev |
| es-module-lexer | 2.3.2 | MIT | dev |
| estree-walker | 3.0.3 | MIT | dev |
| expect-type | 1.4.0 | Apache-2.0 | dev |
| fdir | 6.5.0 | MIT | dev |
| fsevents | 2.3.3 | MIT | dev,optional |
| lightningcss-darwin-arm64 | 1.33.0 | MPL-2.0 | dev,optional |
| lightningcss | 1.33.0 | MPL-2.0 | dev |
| magic-string | 0.30.21 | MIT | dev |
| nanoid | 3.3.20 | MIT | dev |
| obug | 2.2.1 | MIT | dev |
| pathe | 2.0.3 | MIT | dev |
| picocolors | 1.1.1 | ISC | dev |
| picomatch | 4.0.7 | MIT | dev |
| postcss | 8.5.33 | MIT | dev |
| react-dom | 19.3.1 | MIT | runtime |
| react | 19.3.1 | MIT | runtime |
| rolldown | 1.2.19 | MIT | dev |
| scheduler | 0.28.0 | MIT | runtime |
| siginfo | 2.0.0 | ISC | dev |
| source-map-js | 1.2.4 | BSD-3-Clause | dev |
| stackback | 0.0.2 | MIT | dev |
| std-env | 4.3.0 | MIT | dev |
| tinybench | 2.9.0 | MIT | dev |
| tinyexec | 1.4.0 | MIT | dev |
| tinyglobby | 0.2.17 | MIT | dev |
| tinyrainbow | 3.2.0 | MIT | dev |
| typescript | 5.9.3 | Apache-2.0 | dev |
| vitest | 4.1.12 | MIT | dev |
| vite | 8.3.5 | MIT | dev |
| why-is-node-running | 2.3.0 | MIT | dev |

Optional platform packages listed in the lock file but not installed on this machine (macOS arm64): 31 packages, licences from the lock file: MIT 20, MPL-2.0 10 (`lightningcss-*` platform builds), 0BSD 1 (`tslib`).

## Summary

- Installed npm packages: 53 (MIT 45, Apache-2.0 3, ISC 2, MPL-2.0 2, BSD-3-Clause 1); none outside the accepted list. `npm ci` reported "added 53 packages".
- Python packages: 8 installed third-party packages, all in the accepted list.
- Flags: pandoc (GPL-2.0-or-later) and Google Chrome (proprietary) are external tools used to build or check outputs; neither is distributed or linked. The owner decides whether the release notes should name them.

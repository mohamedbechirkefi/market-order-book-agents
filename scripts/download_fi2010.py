# SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0
"""Download the FI-2010 limit-order-book benchmark (CC BY 4.0) into data/raw/.

Deterministic: the source file, its expected SHA-256 and size are fixed below and
were read from the Fairdata Metax record on 2026-11-24. The script

1. asks the Etsin download service for a time-limited download URL for the one
   published file (the dataset is open access; no account is needed),
2. streams it to ``data/raw/fi2010/BenchmarkDatasets.zip``,
3. verifies the SHA-256 and the byte size against the Metax record (fails closed),
4. extracts only the members used by this study (NoAuction, DecPre normalisation,
   anchored fold 9: training days 1..9 and testing day 10), and
5. writes ``data/raw/fi2010/download_record.json`` with URL, date, sizes and hashes.

``data/raw/`` is git-ignored: the archive is 1.86 GB, above the 20 MB limit for
committing redistributable data (owner approvals 2026-11-24b, section 1).

Usage: ``python scripts/download_fi2010.py [--keep-zip] [--skip-download]``.
Standard library only.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import sys
import urllib.request
import zipfile
from pathlib import Path

DATASET_ID = "73eb48d7-4dbc-4a10-a52a-da745b47a649"
FILE_PATH = "/published/BenchmarkDatasets/BenchmarkDatasets.zip"
LANDING_PAGE = f"https://etsin.fairdata.fi/dataset/{DATASET_ID}"
METAX_RECORD = f"https://metax.fairdata.fi/rest/v2/datasets/{DATASET_ID}"
AUTHORIZE_URL = "https://etsin.fairdata.fi/api/v3/download/authorize"
EXPECTED_SHA256 = "cea93692a270724fa91e8f124da641db727d757e5e0f0bb85067709e9932f664"
EXPECTED_BYTES = 1_864_361_899
LICENSE = "CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/)"

# Members extracted (suffix match inside the archive). Fold 9 of the anchored
# cross-validation: the training file holds days 1..9, the testing file day 10.
MEMBERS = (
    "Train_Dst_NoAuction_DecPre_CF_9.txt",
    "Test_Dst_NoAuction_DecPre_CF_9.txt",
)

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "raw" / "fi2010"


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while block := fh.read(chunk):
            h.update(block)
    return h.hexdigest()


def authorize() -> str:
    body = json.dumps({"cr_id": DATASET_ID, "file": FILE_PATH}).encode()
    req = urllib.request.Request(
        AUTHORIZE_URL, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.load(resp)["url"]


def download(url: str, dest: Path) -> None:
    tmp = dest.with_suffix(".part")
    with urllib.request.urlopen(url, timeout=600) as resp, tmp.open("wb") as fh:
        while block := resp.read(1 << 20):
            fh.write(block)
    tmp.rename(dest)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--keep-zip", action="store_true", help="keep the archive after extraction")
    ap.add_argument("--skip-download", action="store_true", help="reuse an existing archive")
    args = ap.parse_args(argv)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    zpath = OUT_DIR / "BenchmarkDatasets.zip"
    accessed = _dt.date.today().isoformat()
    if not args.skip_download:
        download(authorize(), zpath)
    size = zpath.stat().st_size
    digest = sha256_file(zpath)
    if digest != EXPECTED_SHA256 or size != EXPECTED_BYTES:
        print(f"FAILED: sha256 {digest} size {size}; expected {EXPECTED_SHA256} {EXPECTED_BYTES}")
        return 2

    extracted = []
    with zipfile.ZipFile(zpath) as zf:
        names = zf.namelist()
        for want in MEMBERS:
            hits = [n for n in names if n.endswith(want) and "NoAuction" in n]
            if len(hits) != 1:
                print(f"FAILED: member {want} matched {hits}")
                return 3
            target = OUT_DIR / want
            with zf.open(hits[0]) as src, target.open("wb") as dst:
                while block := src.read(1 << 20):
                    dst.write(block)
            extracted.append(
                {
                    "member": hits[0],
                    "path": str(target.relative_to(ROOT)),
                    "bytes": target.stat().st_size,
                    "sha256": sha256_file(target),
                }
            )

    record = {
        "dataset": "FI-2010 (Ntakaris, Magris, Kanniainen, Gabbouj, Iosifidis)",
        "landing_page": LANDING_PAGE,
        "metadata_record": METAX_RECORD,
        "file": FILE_PATH,
        "license": LICENSE,
        "accessed": accessed,
        "archive": {"bytes": size, "sha256": digest, "kept": bool(args.keep_zip)},
        "extracted": extracted,
    }
    (OUT_DIR / "download_record.json").write_text(json.dumps(record, indent=2) + "\n")
    if not args.keep_zip:
        zpath.unlink()
    print(json.dumps(record, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

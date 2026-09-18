"""Download the released weights and annotations from Zenodo.

The imagery is not on Zenodo and cannot be fetched by this script. See
docs/DATA.md for what is released and how to request the rest.

Usage:
    python scripts/fetch_data.py --dest ./data
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

# TO FILL: the numeric Zenodo record id, available once the deposit is
# published. Reserving a DOI on Zenodo before publishing gives you the id
# early, which lets the paper's Data Availability Statement be filled in
# without waiting.
RECORD_ID = None

ZENODO_API = "https://zenodo.org/api/records/{record_id}"


def fetch_record(record_id: int) -> dict:
    url = ZENODO_API.format(record_id=record_id)
    with urllib.request.urlopen(url) as response:
        return json.load(response)


def download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    print(f"  downloading {destination.name}")
    with urllib.request.urlopen(url) as response, open(destination, "wb") as handle:
        while chunk := response.read(1 << 20):
            handle.write(chunk)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", default="./data", help="download directory")
    parser.add_argument("--record-id", type=int, default=RECORD_ID)
    args = parser.parse_args()

    if args.record_id is None:
        print(
            "No Zenodo record id set. Fill RECORD_ID in this file, or pass\n"
            "--record-id. The deposit for this project has not been published\n"
            "yet; see docs/DATA.md."
        )
        return 2

    record = fetch_record(args.record_id)
    destination = Path(args.dest)

    print(f"record: {record['metadata'].get('title', args.record_id)}")
    for entry in record.get("files", []):
        download(entry["links"]["self"], destination / entry["key"])

    print(f"done, files in {destination}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

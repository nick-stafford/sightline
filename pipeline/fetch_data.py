"""Download raw XBRL company facts from SEC EDGAR into cache/.

Run this once (or with --refresh) before build.py. The cached JSON is committed
so the rest of the pipeline runs offline and gives the same numbers every time.

    python fetch_data.py
    python fetch_data.py --refresh
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request

from sightline.config import CACHE_DIR, COHORT, SEC_DELAY, SEC_USER_AGENT

FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"


def fetch_json(url, retries=3):
    """GET a URL and parse JSON, retrying on transient errors."""
    request = urllib.request.Request(url, headers={"User-Agent": SEC_USER_AGENT})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                return json.loads(response.read())
        except (urllib.error.URLError, TimeoutError) as err:
            if attempt == retries - 1:
                raise
            wait = 2 ** attempt
            print(f"    retrying in {wait}s ({err})")
            time.sleep(wait)
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true", help="re-download even if cached")
    args = parser.parse_args()

    CACHE_DIR.mkdir(exist_ok=True)
    failures = []

    for company in COHORT:
        ticker = company["ticker"]
        path = CACHE_DIR / f"{ticker}.json"

        if path.exists() and not args.refresh:
            size_mb = path.stat().st_size / 1_000_000
            print(f"{ticker:6} cached ({size_mb:.1f} MB)")
            continue

        print(f"{ticker:6} downloading...")
        try:
            facts = fetch_json(FACTS_URL.format(cik=company["cik"]))
        except Exception as err:
            print(f"{ticker:6} FAILED: {err}")
            failures.append(ticker)
            continue

        path.write_text(json.dumps(facts), encoding="utf-8")
        print(f"{ticker:6} saved ({path.stat().st_size / 1_000_000:.1f} MB)")
        time.sleep(SEC_DELAY)

    if failures:
        print(f"\nFailed: {', '.join(failures)}")
        return 1
    print(f"\nDone. {len(COHORT)} companies in {CACHE_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

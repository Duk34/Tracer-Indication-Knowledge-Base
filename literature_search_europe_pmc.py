#!/usr/bin/env python3

"""
Candidate literature search (prototype).

Searches Europe PMC (covers PubMed and PMC) for papers that may describe PET imaging tracers and writes a
candidate table (CSV) for manual screening. Through modifying the query it can also 
search for other terms. Nothing is extracted from the
papers yet: the table only lists candidates and their metadata.

Outputs (default folder: data/intermediate/literature/):
- candidates_<timestamp>.csv              one row per unique paper
- raw/europepmc_<timestamp>_q<i>_p<n>.json  unmodified API responses plus the
                                            request that produced them (provenance)

Example:
    python literature_search.py --query '"PET tracer" AND review' --from-year 2020 --to-year 2023 --max-results 200 --output-dir data/literature_search/PET_tracer_reviews

--queries-file allows to pass a text file with one query per line (# = comment)      

Year filter:
- Without --from-year and --to-year, no date filter is applied.
- With only --to-year, the search starts from 1900.
- With only --from-year, the search runs up to today.

DEFAULT QUERIES are [
    '"PET tracer" OR "PET radiotracer"',
    '"PET radioligand" OR "PET radiopharmaceutical"',
    '"positron emission tomography tracer"',
]

DEFAULT for --max-results is 100 (records per query) for testing.

DEFAULT OUTPUT DIRECTORY is Path("data/literature_search")
"""


from __future__ import annotations

import argparse
import json
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pandas as pd

log = logging.getLogger("literature_search")

EPMC_SEARCH_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
REQUEST_TIMEOUT = 30.0  # seconds
PAGE_SIZE = 100  # records per request
PAUSE_SECONDS = 0.5  # pause between requests
MAX_RETRIES = 3
QUERY_SEP = " || "  # separator for the queries that found a paper

# Queries
DEFAULT_QUERIES = [
    '"PET tracer" OR "PET radiotracer"',
    '"PET radioligand" OR "PET radiopharmaceutical"',
    '"positron emission tomography tracer"',
]

DEFAULT_OUTPUT_DIR = Path("data/literature_search")

# Columns of the candidate table.
COLUMNS = [
    "source",
    "source_id",
    "pmid",
    "pmcid",
    "doi",
    "title",
    "authors",
    "journal",
    "year",
    "first_published",
    "pub_types",
    "is_open_access",
    "license",
    "abstract",
    "url",
    "found_by_queries",
    "retrieved_at",
    "notes",
]


# ---------------------------------------------------------------------------
# Query building and API access
# ---------------------------------------------------------------------------
def build_query(query: str, from_year: int | None = None, to_year: int | None = None) -> str:
    #Add an optional publication-date filter to a Europe PMC query.
    if from_year is None and to_year is None:
        return query
    start = f"{from_year}-01-01" if from_year else "1900-01-01"
    end = f"{to_year}-12-31" if to_year else datetime.now(timezone.utc).date().isoformat()
    return f"({query}) AND (FIRST_PDATE:[{start} TO {end}])"


def get_json(client: httpx.Client, params: dict) -> dict:
    #GET the search endpoint with a few retries; return the parsed JSON.
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.get(EPMC_SEARCH_URL, params=params)
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            log.warning("Request failed (attempt %d/%d): %s", attempt, MAX_RETRIES, exc)
            if attempt == MAX_RETRIES:
                raise
            time.sleep(2**attempt)


def save_raw(data: dict, params: dict, path: Path) -> None:
    #Store an API response together with the request that produced it.
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "request": {
            "url": EPMC_SEARCH_URL,
            "params": params,
            "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        },
        "response": data,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def search_europe_pmc(
    client: httpx.Client,
    query: str,
    max_results: int,
    raw_dir: Path,
    stamp: str,
    query_index: int = 1,
) -> list[dict]:
    #Return up to max_results raw records for a query, following the cursor.
    results: list[dict] = []
    cursor = "*"
    page = 0

    while len(results) < max_results:
        params = {
            "query": query,
            "format": "json",
            "resultType": "core",
            "pageSize": min(PAGE_SIZE, max_results - len(results)),
            "cursorMark": cursor,
        }
        data = get_json(client, params)
        page += 1
        save_raw(data, params, raw_dir / f"europepmc_{stamp}_q{query_index}_p{page}.json")

        if page == 1:
            log.info("Query %d: %s hits in total", query_index, data.get("hitCount", "?"))

        page_results = (data.get("resultList") or {}).get("result") or []
        if not page_results:
            break
        results.extend(page_results)

        next_cursor = data.get("nextCursorMark")
        if not next_cursor or next_cursor == cursor:
            break
        cursor = next_cursor
        time.sleep(PAUSE_SECONDS)

    return results[:max_results]


# ---------------------------------------------------------------------------
# Parsing and cleaning
# ---------------------------------------------------------------------------
def clean_text(text: str | None) -> str:
    #Remove markup tags and collapse whitespace (abstracts can contain HTML).
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_doi(doi: str | None) -> str:
    #Lower-case a DOI and strip URL or 'doi:' prefixes.
    if not doi:
        return ""
    doi = doi.strip().lower()
    doi = re.sub(r"^(https?://)?(dx\.)?doi\.org/", "", doi)
    return doi.removeprefix("doi:").strip()


def parse_record(raw: dict, query: str, retrieved_at: str) -> dict:
    #Map one raw Europe PMC record to the columns of the candidate table.
    source = raw.get("source", "")
    source_id = raw.get("id", "")
    journal = (raw.get("journalInfo") or {}).get("journal") or {}
    pub_types = (raw.get("pubTypeList") or {}).get("pubType") or []

    return {
        "source": source,
        "source_id": source_id,
        "pmid": raw.get("pmid", ""),
        "pmcid": raw.get("pmcid", ""),
        "doi": normalize_doi(raw.get("doi")),
        "title": clean_text(raw.get("title")),
        "authors": raw.get("authorString", ""),
        "journal": journal.get("title", ""),
        "year": raw.get("pubYear", ""),
        "first_published": raw.get("firstPublicationDate", ""),
        "pub_types": "; ".join(pub_types),
        "is_open_access": raw.get("isOpenAccess", ""),
        "license": raw.get("license", ""),
        "abstract": clean_text(raw.get("abstractText")),
        "url": f"https://europepmc.org/article/{source}/{source_id}" if source and source_id else "",
        "found_by_queries": query,
        "retrieved_at": retrieved_at,
    }


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------
def dedup_key(record: dict) -> str:
    #Same DOI means same paper; without a DOI use the source-specific ID.
    if record["doi"]:
        return f"doi:{record['doi']}"
    return f"{record['source']}:{record['source_id']}"


def deduplicate(records: list[dict]) -> list[dict]:
    """Merge duplicate records, remembering every query that found a paper.

    A preprint and its published version usually have different DOIs and are
    therefore kept as separate rows (to be linked later).
    """
    merged: dict[str, dict] = {}
    for record in records:
        key = dedup_key(record)
        if key not in merged:
            merged[key] = dict(record)
            continue

        kept = merged[key]
        queries = kept["found_by_queries"].split(QUERY_SEP)
        if record["found_by_queries"] not in queries:
            kept["found_by_queries"] += QUERY_SEP + record["found_by_queries"]
        for column in ("pmid", "pmcid", "abstract", "license"):  # fill gaps
            if not kept[column] and record[column]:
                kept[column] = record[column]
    return list(merged.values())


# ---------------------------------------------------------------------------
# Command line interface
# ---------------------------------------------------------------------------
def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Search Europe PMC for candidate tracer papers.")
    parser.add_argument("--query", action="append", help="Europe PMC query (can be given several times)")
    parser.add_argument("--queries-file", type=Path, help="text file with one query per line (# = comment)")
    parser.add_argument("--from-year", type=int, help="earliest publication year")
    parser.add_argument("--to-year", type=int, help="latest publication year")
    parser.add_argument("--max-results", type=int, default=100, help="maximum records per query")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args(argv)


def load_queries(args: argparse.Namespace) -> list[str]:
    queries = list(args.query or [])
    if args.queries_file:
        lines = args.queries_file.read_text(encoding="utf-8").splitlines()
        stripped = [line.strip() for line in lines]
        from_file = [line for line in stripped if line and not line.startswith("#")]
        if not from_file:
            raise SystemExit(f"No queries found in {args.queries_file} (only comments or empty lines).")
        queries += from_file
    if not queries:
        log.info("No queries given, using DEFAULT_QUERIES")
        return DEFAULT_QUERIES
    return queries


def main(argv: list[str] | None = None) -> Path:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = parse_args(argv)
    queries = load_queries(args)

    raw_dir = args.output_dir / "raw"
    run_stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    retrieved_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    user_agent = "tracer-ikb-literature-search"

    records: list[dict] = []
    with httpx.Client(timeout=REQUEST_TIMEOUT, headers={"User-Agent": user_agent}) as client:
        for index, query in enumerate(queries, start=1):
            full_query = build_query(query, args.from_year, args.to_year)
            raw_results = search_europe_pmc(client, full_query, args.max_results, raw_dir, run_stamp, index)
            records += [parse_record(raw, full_query, retrieved_at) for raw in raw_results]

    unique = deduplicate(records)
    df = pd.DataFrame(unique, columns=COLUMNS)

    # A new file per run, so manual edits in "notes" are never overwritten.
    out_path = args.output_dir / f"candidates_{run_stamp}.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False, encoding="utf-8")

    log.info("%d records found, %d unique papers -> %s", len(records), len(df), out_path)
    return out_path


if __name__ == "__main__":
    main()
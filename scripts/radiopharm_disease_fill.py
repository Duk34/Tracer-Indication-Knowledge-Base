"""
Expand the radiopharmaceutical table by disease indication and evidence level.

Uses the existing Radiopharm ID and getDrugInfo API response.
"""

try:
    from .config import (
        INTEGRATED_TABLE_RADIOPHARM_POPULATED,
        INTEGRATED_TABLE_RADIOPHARM,
        INTEGRATED_TABLE_DISEASE_EXPANDED,
        RADIOPHARM_INFO_API,
    )
except ImportError:
    from config import (
        INTEGRATED_TABLE_RADIOPHARM_POPULATED,
        INTEGRATED_TABLE_RADIOPHARM,
        INTEGRATED_TABLE_DISEASE_EXPANDED,
        RADIOPHARM_INFO_API,
    )

import re

import httpx
import pandas as pd


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows/10.0) AppleWebKit/537.36 "
        "Chrome/160.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
}


def map_evidence_level(phase: object) -> int | None:
    if pd.isna(phase):
        return None

    text = str(phase).lower().strip()
    if "preclinical" in text or "pre-clinical" in text:
        return 1
    if "approved" in text or "approval" in text:
        return 4
    if re.search(r"\bphase\s*(?:[i]+\b|[1-2]\b)", text):
        return 2
    if re.search(r"\b(?:phase\s*)?(?:3|4|iii|iv)\b", text):
        return 3
    if "fda" in text or "ema" in text:
        return 4
    return None


def extract_year(indication: dict, refs: dict) -> int | None:
    reference_ids = indication.get("indication_ref", [])
    if isinstance(reference_ids, str):
        reference_ids = [reference_ids]
    if not isinstance(reference_ids, list):
        reference_ids = []

    candidates = list(reference_ids)
    for reference_id in reference_ids:
        reference = refs.get(str(reference_id), {})
        if isinstance(reference, dict):
            candidates.extend(str(reference.get(field, "")) for field in (
                "year",
                "title",
                "journal",
                "pmid",
                "url",
            ))

    candidates.append(str(indication.get("indication_ref", "")))

    years = []
    for candidate in candidates:
        for match in re.findall(r"\b(19\d{2}|20\d{2})\b", str(candidate)):
            year = int(match)
            if 1900 <= year <= 2100:
                years.append(year)
    return min(years) if years else None


def get_json(client: httpx.Client, url: str) -> dict | None:
    try:
        response = client.get(url)
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, dict) else None
    except httpx.HTTPError as exc:
        print(f"Request failed for {url}: {exc}")
        return None
    except ValueError as exc:
        print(f"Invalid JSON returned by {url}: {exc}")
        return None


def main() -> int:
    input_path = (
        INTEGRATED_TABLE_RADIOPHARM_POPULATED
        if INTEGRATED_TABLE_RADIOPHARM_POPULATED.exists()
        else INTEGRATED_TABLE_RADIOPHARM
    )
    df = pd.read_csv(input_path)

    for column in ("Disease name", "Evidence Level", "Year"):
        if column not in df.columns:
            df[column] = pd.NA

    df["Disease name"] = df["Disease name"].astype("object")
    df["Evidence Level"] = df["Evidence Level"].astype("object")
    df["Year"] = df["Year"].astype("object")

    expanded_rows = []

    with httpx.Client(
        headers=HEADERS,
        timeout=20.0,
        follow_redirects=True,
    ) as client:
        for _, row in df.iterrows():
            radiopharm_id = row.get("Radiopharm_ID")
            if pd.isna(radiopharm_id) or not str(radiopharm_id).strip():
                expanded_rows.append(row.to_dict())
                continue

            url = f"{RADIOPHARM_INFO_API}/{str(radiopharm_id).strip()}"
            info = get_json(client, url)
            indications = []
            refs = {}

            if info:
                general_info = info.get("general_info", {})
                if isinstance(general_info, dict):
                    api_indications = general_info.get("indication", [])
                    if isinstance(api_indications, list):
                        indications = api_indications
                    api_refs = general_info.get("refs", {})
                    if isinstance(api_refs, dict):
                        refs = api_refs

            if not indications:
                expanded_rows.append(row.to_dict())
                continue

            seen = set()
            for indication in indications:
                if not isinstance(indication, dict):
                    continue

                disease_name = indication.get("clinical_indication")
                if disease_name is None:
                    continue
                disease_name = str(disease_name).strip()
                if not disease_name:
                    continue

                evidence_level = map_evidence_level(indication.get("phase"))
                disease_key = disease_name.casefold()
                key = (disease_key, evidence_level)
                if key in seen:
                    continue
                seen.add(key)

                new_row = row.to_dict()
                new_row["Disease name"] = disease_name
                new_row["Evidence Level"] = evidence_level

                api_year = extract_year(indication, refs)
                existing_year = row.get("Year")
                if pd.isna(existing_year) and api_year is not None:
                    new_row["Year"] = api_year

                expanded_rows.append(new_row)

    result = pd.DataFrame(expanded_rows, columns=df.columns)

    if "Evidence Level" in result.columns:
        result["Evidence Level"] = pd.to_numeric(
            result["Evidence Level"], errors="coerce"
        ).astype("Int64")
    if "Year" in result.columns:
        result["Year"] = pd.to_numeric(
            result["Year"], errors="coerce"
        ).astype("Int64")

    result = result.drop_duplicates(
        subset=["Tracer_ID", "Disease name", "Evidence Level"],
        keep="first",
    )
    result.to_csv(INTEGRATED_TABLE_DISEASE_EXPANDED, index=False)
    print(
        "Disease-expanded table saved to "
        f"{INTEGRATED_TABLE_DISEASE_EXPANDED}"
    )
    print(f"Rows: {len(result)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

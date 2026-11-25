"""Step: one row per tracer and disease, with evidence level and year, from RadioPharm."""

import re

import pandas as pd

from tikb.enrich.radiopharm.client import DRUG_INFO_URL, get_json, new_client


def map_evidence_level(phase: object) -> int | None:
    """Clinical phase -> evidence level (4 = approved ... 1 = preclinical)."""
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
    """Earliest year found in the references of an indication."""
    reference_ids = indication.get("indication_ref", [])
    if isinstance(reference_ids, str):
        reference_ids = [reference_ids]
    if not isinstance(reference_ids, list):
        reference_ids = []

    candidates = list(reference_ids)
    for reference_id in reference_ids:
        reference = refs.get(str(reference_id), {})
        if isinstance(reference, dict):
            candidates += [
                str(reference.get(f, ""))
                for f in ("year", "title", "journal", "pmid", "url")
            ]
    candidates.append(str(indication.get("indication_ref", "")))

    years = [
        int(y) for c in candidates for y in re.findall(r"\b(19\d{2}|20\d{2})\b", str(c))
    ]
    return min(years) if years else None


def expand_diseases(df: pd.DataFrame) -> pd.DataFrame:
    """Make one row per tracer and disease, with evidence level and year."""
    for column in ("Disease name", "Evidence Level", "Year"):
        if column not in df.columns:
            df[column] = pd.NA
        df[column] = df[column].astype("object")

    rows = []
    with new_client() as client:
        for _, row in df.iterrows():
            radiopharm_id = row.get("Radiopharm_ID")
            if pd.isna(radiopharm_id) or not str(radiopharm_id).strip():
                rows.append(row.to_dict())
                continue

            info = get_json(client, f"{DRUG_INFO_URL}/{str(radiopharm_id).strip()}")
            general_info = (info or {}).get("general_info", {})
            if not isinstance(general_info, dict):
                general_info = {}
            indications = general_info.get("indication", [])
            refs = general_info.get("refs", {})
            if not isinstance(indications, list) or not indications:
                rows.append(row.to_dict())
                continue
            if not isinstance(refs, dict):
                refs = {}

            seen = set()
            for indication in indications:
                if not isinstance(indication, dict):
                    continue
                disease = str(indication.get("clinical_indication") or "").strip()
                if not disease:
                    continue
                evidence_level = map_evidence_level(indication.get("phase"))
                key = (disease.casefold(), evidence_level)
                if key in seen:
                    continue
                seen.add(key)

                new_row = row.to_dict()
                new_row["Disease name"] = disease
                new_row["Evidence Level"] = evidence_level
                year = extract_year(indication, refs)
                if pd.isna(row.get("Year")) and year is not None:
                    new_row["Year"] = year
                rows.append(new_row)

    result = pd.DataFrame(rows, columns=df.columns)
    result["Evidence Level"] = pd.to_numeric(
        result["Evidence Level"], errors="coerce"
    ).astype("Int64")
    result["Year"] = pd.to_numeric(result["Year"], errors="coerce").astype("Int64")
    return result.drop_duplicates(
        subset=["Tracer_ID", "Disease name", "Evidence Level"]
    )

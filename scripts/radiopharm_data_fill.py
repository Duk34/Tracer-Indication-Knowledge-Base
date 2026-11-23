"""
Populate the radiopharmaceutical table using the RadioPharm REST API.
"""

try:
    from .config import (
        INTEGRATED_TABLE_RADIOPHARM,
        INTEGRATED_TABLE_RADIOPHARM_POPULATED,
        RADIOPHARM_INFO_API,
        RADIOPHARM_DRUG_DESCRIPTION,
        RADIOPHARM_TARGET_INFO,
    )
except ImportError:
    from config import (
        INTEGRATED_TABLE_RADIOPHARM,
        INTEGRATED_TABLE_RADIOPHARM_POPULATED,
        RADIOPHARM_INFO_API,
        RADIOPHARM_DRUG_DESCRIPTION,
        RADIOPHARM_TARGET_INFO,
    )

import pandas as pd
import httpx


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:160.0) "
        "Gecko/20100101 Firefox/160.0"
    ),
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://radiopharm.idrblab.cn",
    "Referer": "https://radiopharm.idrblab.cn/search-drug",
}


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


def get_target_ids(description: dict) -> list[str]:
    targets = description.get("description_targets", [])
    target_ids = []

    if not isinstance(targets, list):
        return target_ids

    for target in targets:
        if not isinstance(target, dict):
            continue

        target_id = target.get("target_id")
        if not target_id and isinstance(target.get("target_info"), dict):
            target_id = target["target_info"].get("target_id")

        if target_id:
            target_ids.append(str(target_id))

    return list(dict.fromkeys(target_ids))


def normalize_type(drug_type: object) -> str | None:
    if pd.isna(drug_type):
        return None

    normalized = str(drug_type).strip().lower()
    if "antibody" in normalized:
        return "antibody"
    if "peptide" in normalized:
        return "peptide"
    if "compound" in normalized or "element" in normalized:
        return "small molecule"
    if "small molecule" in normalized:
        return "small molecule"
    return None


def merge_ids(existing: object, *new_values: object) -> str | None:
    ids = []
    for value in (existing, *new_values):
        if pd.isna(value):
            continue
        for item in str(value).split(";"):
            item = item.strip()
            if item and item not in ids:
                ids.append(item)
    return ";".join(ids) if ids else None


def merge_synonyms(existing: object, *new_values: object) -> str | None:
    synonyms = []
    seen = set()

    for value in (existing, *new_values):
        if pd.isna(value):
            continue
        for synonym in str(value).split(";"):
            synonym = synonym.strip()
            normalized = " ".join(synonym.split()).casefold()
            if synonym and normalized not in seen:
                seen.add(normalized)
                synonyms.append(synonym)

    return ";".join(synonyms) if synonyms else None


def main() -> int:
    df = pd.read_csv(INTEGRATED_TABLE_RADIOPHARM)
    df["Type"] = df["Type"].astype("object")
    df["Synonyms"] = df["Synonyms"].astype("object")
    df["Target protein_ID"] = df["Target protein_ID"].astype("object")
    df["Target gene_ID"] = df["Target gene_ID"].astype("object")
    df["Source (URL)"] = df["Source (URL)"].astype("object")

    with httpx.Client(
        headers=HEADERS,
        timeout=20.0,
        follow_redirects=True,
    ) as client:
        for index, row in df.iterrows():
            radiopharm_id = row.get("Radiopharm_ID")
            if pd.isna(radiopharm_id):
                continue

            radiopharm_id = str(radiopharm_id).strip()
            if not radiopharm_id:
                continue

            info_url = f"{RADIOPHARM_INFO_API}/{radiopharm_id}"
            description_url = f"{RADIOPHARM_DRUG_DESCRIPTION}/{radiopharm_id}"

            info = get_json(client, info_url)
            description = get_json(client, description_url)

            if info:
                general_info = info.get("general_info", {})
                if isinstance(general_info, dict):
                    drug_type = general_info.get("drug_type")
                    if drug_type:
                        df.at[index, "Type"] = normalize_type(drug_type)

                    api_synonyms = general_info.get("synonyms")
                    if api_synonyms:
                        df.at[index, "Synonyms"] = merge_synonyms(
                            row.get("Synonyms"),
                            api_synonyms,
                        )

            df.at[index, "Source (URL)"] = info_url

            if not description:
                continue

            uniprot_ids = []
            gene_ids = []
            for target_id in get_target_ids(description):
                target_url = f"{RADIOPHARM_TARGET_INFO}/{target_id}"
                target = get_json(client, target_url)
                if not target:
                    continue

                target_info = target.get("general_info", {})
                if not isinstance(target_info, dict):
                    continue

                uniprot_id = target_info.get("uniprot_id")
                gene_id = target_info.get("gene_id")
                if uniprot_id:
                    uniprot_ids.append(str(uniprot_id))
                if gene_id:
                    gene_ids.append(str(gene_id))

            df.at[index, "Target protein_ID"] = (
                merge_ids(row.get("Target protein_ID"), *uniprot_ids)
            )
            df.at[index, "Target gene_ID"] = (
                merge_ids(row.get("Target gene_ID"), *gene_ids)
            )

            print(f"Populated {row['Tracer_ID']} ({radiopharm_id})")

    df["Type"] = df["Type"].map(normalize_type)
    df.to_csv(INTEGRATED_TABLE_RADIOPHARM_POPULATED, index=False)
    print(
        f"Populated radiopharmaceutical table saved to "
        f"{INTEGRATED_TABLE_RADIOPHARM_POPULATED}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

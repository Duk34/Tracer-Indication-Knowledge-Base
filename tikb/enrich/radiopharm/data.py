"""Step: fill Type, Synonyms, Source (URL) and target IDs from RadioPharm."""

import pandas as pd

from tikb.enrich.radiopharm.client import (
    DRUG_DESCRIPTION_URL,
    DRUG_INFO_URL,
    TARGET_URL,
    get_json,
    new_client,
)
from tikb.utils import merge_ids


def normalize_type(drug_type: object) -> str | None:
    if pd.isna(drug_type):
        return None
    text = str(drug_type).strip().lower()
    if "antibody" in text:
        return "antibody"
    if "peptide" in text:
        return "peptide"
    if "compound" in text or "element" in text or "small molecule" in text:
        return "small molecule"
    return None


def merge_synonyms(*values: object) -> str | None:
    """Like merge_ids, but ignores case and extra spaces when looking for duplicates."""
    synonyms, seen = [], set()
    for value in values:
        if pd.isna(value):
            continue
        for synonym in str(value).split(";"):
            synonym = synonym.strip()
            key = " ".join(synonym.split()).casefold()
            if synonym and key not in seen:
                seen.add(key)
                synonyms.append(synonym)
    return ";".join(synonyms) if synonyms else None


def get_target_ids(description: dict) -> list[str]:
    """RadioPharm target IDs listed in a getDrugDescription answer."""
    targets = description.get("description_targets", [])
    if not isinstance(targets, list):
        return []
    target_ids = []
    for target in targets:
        if not isinstance(target, dict):
            continue
        target_id = target.get("target_id")
        if not target_id and isinstance(target.get("target_info"), dict):
            target_id = target["target_info"].get("target_id")
        if target_id:
            target_ids.append(str(target_id))
    return list(dict.fromkeys(target_ids))


def add_radiopharm_data(df: pd.DataFrame) -> pd.DataFrame:
    """Fill Type, Synonyms, Source (URL) and target IDs from RadioPharm."""
    for column in (
        "Type",
        "Synonyms",
        "Target protein_ID",
        "Target gene_ID",
        "Source (URL)",
    ):
        df[column] = df[column].astype("object")

    with new_client() as client:
        for index, row in df.iterrows():
            radiopharm_id = row.get("Radiopharm_ID")
            if pd.isna(radiopharm_id) or not str(radiopharm_id).strip():
                continue
            radiopharm_id = str(radiopharm_id).strip()

            info_url = f"{DRUG_INFO_URL}/{radiopharm_id}"
            info = get_json(client, info_url)
            description = get_json(client, f"{DRUG_DESCRIPTION_URL}/{radiopharm_id}")

            general_info = (info or {}).get("general_info", {})
            if isinstance(general_info, dict):
                if general_info.get("drug_type"):
                    df.at[index, "Type"] = normalize_type(general_info["drug_type"])
                if general_info.get("synonyms"):
                    df.at[index, "Synonyms"] = merge_synonyms(
                        row.get("Synonyms"), general_info["synonyms"]
                    )
            df.at[index, "Source (URL)"] = info_url

            if not description:
                continue

            uniprot_ids, gene_ids = [], []
            for target_id in get_target_ids(description):
                target = get_json(client, f"{TARGET_URL}/{target_id}")
                target_info = (target or {}).get("general_info", {})
                if not isinstance(target_info, dict):
                    continue
                if target_info.get("uniprot_id"):
                    uniprot_ids.append(str(target_info["uniprot_id"]))
                if target_info.get("gene_id"):
                    gene_ids.append(str(target_info["gene_id"]))

            df.at[index, "Target protein_ID"] = merge_ids(
                row.get("Target protein_ID"), *uniprot_ids
            )
            df.at[index, "Target gene_ID"] = merge_ids(
                row.get("Target gene_ID"), *gene_ids
            )
            print(f"Populated {row['Tracer_ID']} ({radiopharm_id})")

    df["Type"] = df["Type"].map(normalize_type)
    return df

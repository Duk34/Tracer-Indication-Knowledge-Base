"""
Translate target protein names into UniProt and NCBI Gene IDs.

Run this script before radiopharm_data_fill.py.
"""

try:
    from .config import (
        INTEGRATED_TABLE_SYNONYMS,
        INTEGRATED_TABLE_PROTEIN_ID,
        TARGET_ID_MAPPING,
    )
except ImportError:
    from config import (
        INTEGRATED_TABLE_SYNONYMS,
        INTEGRATED_TABLE_PROTEIN_ID,
        TARGET_ID_MAPPING,
    )

import pandas as pd
import mygene
import re


def split_target_name(value: object) -> list[str]:
    if pd.isna(value):
        return []

    text = str(value).strip()
    if not text:
        return []

    parts = []
    for semicolon_part in text.split(";"):
        parts.extend(part.strip() for part in semicolon_part.split("/") if part.strip())
    return list(dict.fromkeys(parts))


def swiss_prot_id(uniprot: object) -> str | None:
    if isinstance(uniprot, dict):
        swiss_prot = uniprot.get("Swiss-Prot")
        if isinstance(swiss_prot, list):
            return str(swiss_prot[0]) if swiss_prot else None
        if swiss_prot:
            return str(swiss_prot)
    return None


def merge_ids(*values: object) -> str | None:
    ids = []
    for value in values:
        if pd.isna(value):
            continue
        for item in str(value).split(";"):
            item = item.strip()
            if item and item not in ids:
                ids.append(item)
    return ";".join(ids) if ids else None


def query_mygene(name: str, client: mygene.MyGeneInfo) -> tuple[str | None, str | None]:
    matches = client.querymany(
        [name],
        scopes="symbol,name,alias",
        fields="symbol,entrezgene,uniprot",
        species="human",
    )

    for match in matches:
        if "notfound" in match:
            continue

        symbol = str(match.get("symbol", "")).strip()
        if symbol.lower() != name.lower():
            continue

        protein_id = swiss_prot_id(match.get("uniprot"))
        gene_id = match.get("entrezgene")
        return protein_id, str(gene_id) if gene_id is not None else None

    return None, None


def map_target_name(name: str, client: mygene.MyGeneInfo) -> tuple[str | None, str | None]:
    fallback = TARGET_ID_MAPPING.get(name)
    if fallback:
        return fallback["protein"], fallback["gene"]

    protein_id, gene_id = query_mygene(name, client)
    if protein_id or gene_id:
        return protein_id, gene_id

    fallback = TARGET_ID_MAPPING.get(name.lower())
    if fallback:
        return fallback["protein"], fallback["gene"]

    return None, None


def main() -> int:
    df = pd.read_csv(INTEGRATED_TABLE_SYNONYMS)
    df["Target protein_ID"] = df["Target protein_ID"].astype("object")
    df["Target gene_ID"] = df["Target gene_ID"].astype("object")

    client = mygene.MyGeneInfo()
    unresolved = []

    for index, value in df["Target protein_ID"].items():
        if pd.isna(value):
            continue

        text = str(value).strip()
        if not text:
            continue

        fallback = TARGET_ID_MAPPING.get(text)
        if fallback:
            protein_ids = fallback["protein"]
            gene_ids = fallback["gene"]
        else:
            protein_ids = []
            gene_ids = []

            for name in split_target_name(text):
                if re.fullmatch(r"[OPQ][0-9][A-Z0-9]{3}[0-9]", name):
                    protein_ids.append(name)
                    continue
                protein_id, gene_id = map_target_name(name, client)
                if protein_id:
                    protein_ids.append(protein_id)
                if gene_id:
                    gene_ids.append(gene_id)
                if not protein_id and not gene_id:
                    unresolved.append(name)

            protein_ids = merge_ids(*protein_ids)
            gene_ids = merge_ids(*gene_ids)

        df.at[index, "Target protein_ID"] = protein_ids
        df.at[index, "Target gene_ID"] = merge_ids(
            df.at[index, "Target gene_ID"],
            gene_ids,
        )

    df.to_csv(INTEGRATED_TABLE_PROTEIN_ID, index=False)
    print(f"Mapped target table saved to {INTEGRATED_TABLE_PROTEIN_ID}")

    unresolved = list(dict.fromkeys(unresolved))
    if unresolved:
        print("Unresolved target names:")
        for name in unresolved:
            print(f"  - {name}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

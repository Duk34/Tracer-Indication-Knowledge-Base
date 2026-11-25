"""Translate target names (e.g. "PSMA", "SSTR") into UniProt and NCBI Gene IDs with MyGene.info."""

import re

import mygene
import pandas as pd

from tikb.utils import merge_ids

# Fallbacks for target names that MyGene cannot resolve reliably.
# Values are semicolon-separated for protein complexes or several subunits.
TARGET_ID_MAPPING = {
    "AMPAR": {"protein": "P42261;P42262;P42263;P48058", "gene": "2890;2891;2892;2893"},
    "Aβ": {"protein": "P05067", "gene": "351"},
    "CB1R/CB2R": {"protein": "P21554;P34972", "gene": "1268;1281"},
    "CD3": {"protein": "P04234;P07766;P09693", "gene": "915;916;917"},
    "CD8": {"protein": "P01732;P10966", "gene": "925;926"},
    "FAP": {"protein": "Q12884", "gene": "2191"},
    "FAAH": {"protein": "O00519", "gene": "2166"},
    "GRPR": {"protein": "P30550", "gene": "2925"},
    "Granzyme B": {"protein": "P10144", "gene": "3002"},
    "IDO": {"protein": "P14902", "gene": "3620"},
    "Integrin": {"protein": "P06756;P05106", "gene": "3685;3690"},
    "MAGL": {"protein": "Q99685", "gene": "11343"},
    "Nectin-4": {"protein": "Q96NY8", "gene": "81607"},
    "NTSR-1": {"protein": "P30989", "gene": "4914"},
    "PD-1": {"protein": "Q15116", "gene": "5133"},
    "PD-L1": {"protein": "Q9NZQ7", "gene": "29126"},
    "PSMA": {"protein": "Q04609", "gene": "2346"},
    "SSTR": {"protein": "P30874", "gene": "6752"},
    "Sigma receptors": {"protein": "Q99720", "gene": "10280"},
    "Tau": {"protein": "P10636", "gene": "4137"},
    "UPAR": {"protein": "Q03405", "gene": "5329"},
    "VMAT2": {"protein": "Q05940", "gene": "6571"},
    "α-synuclein": {"protein": "P37840", "gene": "6622"},
}

UNIPROT_ID = r"[OPQ][0-9][A-Z0-9]{3}[0-9]"


def split_target_name(value: object) -> list[str]:
    """ "PSMA/FAP; SSTR" -> ["PSMA", "FAP", "SSTR"]"""
    if pd.isna(value):
        return []
    parts = []
    for semicolon_part in str(value).split(";"):
        parts.extend(part.strip() for part in semicolon_part.split("/") if part.strip())
    return list(dict.fromkeys(parts))


def swiss_prot_id(uniprot: object) -> str | None:
    """Pick the reviewed (Swiss-Prot) UniProt ID from a MyGene result."""
    if isinstance(uniprot, dict):
        swiss_prot = uniprot.get("Swiss-Prot")
        if isinstance(swiss_prot, list):
            return str(swiss_prot[0]) if swiss_prot else None
        if swiss_prot:
            return str(swiss_prot)
    return None


def query_mygene(name: str, client: mygene.MyGeneInfo) -> tuple[str | None, str | None]:
    """Return (UniProt ID, Gene ID) for a human gene whose symbol equals name."""
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
        gene_id = match.get("entrezgene")
        return swiss_prot_id(match.get("uniprot")), str(gene_id) if gene_id else None
    return None, None


def map_target_name(
    name: str, client: mygene.MyGeneInfo
) -> tuple[str | None, str | None]:
    fallback = TARGET_ID_MAPPING.get(name) or TARGET_ID_MAPPING.get(name.lower())
    if fallback:
        return fallback["protein"], fallback["gene"]
    return query_mygene(name, client)


def add_target_ids(df: pd.DataFrame) -> pd.DataFrame:
    """Replace target names in "Target protein_ID" with UniProt IDs and fill "Target gene_ID"."""
    df["Target protein_ID"] = df["Target protein_ID"].astype("object")
    df["Target gene_ID"] = df["Target gene_ID"].astype("object")
    client = mygene.MyGeneInfo()
    unresolved = []

    for index, value in df["Target protein_ID"].items():
        if pd.isna(value) or not str(value).strip():
            continue
        text = str(value).strip()

        fallback = TARGET_ID_MAPPING.get(text)
        if fallback:
            protein_ids, gene_ids = fallback["protein"], fallback["gene"]
        else:
            proteins, genes = [], []
            for name in split_target_name(text):
                if re.fullmatch(UNIPROT_ID, name):
                    proteins.append(name)
                    continue
                protein_id, gene_id = map_target_name(name, client)
                if protein_id:
                    proteins.append(protein_id)
                if gene_id:
                    genes.append(gene_id)
                if not protein_id and not gene_id:
                    unresolved.append(name)
            protein_ids, gene_ids = merge_ids(*proteins), merge_ids(*genes)

        df.at[index, "Target protein_ID"] = protein_ids
        df.at[index, "Target gene_ID"] = merge_ids(
            df.at[index, "Target gene_ID"], gene_ids
        )

    for name in dict.fromkeys(unresolved):
        print(f"Unresolved target name: {name}")
    return df

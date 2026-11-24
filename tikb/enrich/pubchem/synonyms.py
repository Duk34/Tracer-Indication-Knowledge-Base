"""Step: add the PubChem synonyms of each CID/SID to the existing synonyms."""

import pandas as pd
import pubchempy

from tikb.enrich.pubchem.client import call_with_retry


def cid_synonyms(cid: int) -> list[str]:
    synonyms = call_with_retry(lambda: pubchempy.Compound.from_cid(cid).synonyms)
    return synonyms or []


def sid_synonyms(sid: int) -> list[str]:
    synonyms = call_with_retry(lambda: pubchempy.Substance.from_sid(sid).synonyms)
    return synonyms or []


def split_synonyms(values: pd.Series) -> set[str]:
    """All synonyms of the given cells as a set ("a;b", "b;c" -> {a, b, c})."""
    synonyms = set()
    for value in values.dropna():
        synonyms.update(s.strip() for s in str(value).split(";") if s.strip())
    return synonyms


def add_synonyms(df: pd.DataFrame) -> pd.DataFrame:
    """Add the PubChem synonyms of each CID/SID to the existing synonyms."""
    df["Synonyms"] = df["Synonyms"].astype("object")
    for id_column, fetch in (("CID", cid_synonyms), ("SID", sid_synonyms)):
        has_id = df[id_column].notna()
        for pubchem_id in df.loc[has_id, id_column].unique():
            rows = has_id & (df[id_column] == pubchem_id)
            synonyms = split_synonyms(df.loc[rows, "Synonyms"])
            synonyms.update(s.strip() for s in fetch(int(pubchem_id)) if s.strip())
            if synonyms:
                df.loc[rows, "Synonyms"] = ";".join(sorted(synonyms))
    return df

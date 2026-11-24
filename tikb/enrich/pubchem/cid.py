"""Step: add PubChem Compound IDs (CID)."""

import pandas as pd
import pubchempy

from tikb.enrich.pubchem.client import call_with_retry
from tikb.enrich.pubchem.names import look_up_tracers


def cid_for_name(name: str) -> int | None:
    compounds = call_with_retry(pubchempy.get_compounds, name, "name")
    return compounds[0].cid if compounds else None


def add_cids(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fill the CID column for every tracer."""
    tracers = df["Tracer_ID"].dropna().unique()
    cids, matches = look_up_tracers(tracers, cid_for_name, "CID")
    df["CID"] = df["Tracer_ID"].map(cids).astype("Int64")
    return df, matches

"""Step: add PubChem Substance IDs (SID) for tracers without a CID."""

import pandas as pd
import pubchempy

from tikb.enrich.pubchem.client import call_with_retry
from tikb.enrich.pubchem.names import look_up_tracers


def sid_for_name(name: str) -> int | None:
    substances = call_with_retry(pubchempy.get_substances, name, "name")
    return substances[0].sid if substances else None


def add_sids(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fill the SID column, only for tracers without a CID."""
    no_cid = df["CID"].isna()
    tracers = df.loc[no_cid, "Tracer_ID"].dropna().unique()
    sids, matches = look_up_tracers(tracers, sid_for_name, "SID")
    df.loc[no_cid, "SID"] = df.loc[no_cid, "Tracer_ID"].map(sids)
    df["SID"] = df["SID"].astype("Int64")
    return df, matches

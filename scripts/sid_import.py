import re
import time
import pandas as pd
import pubchempy

try:
    from .config import *
except ImportError:
    from config import *

from cid_import import (
    remove_brackets_from_compound_names,
    generate_permutations,
)

LOG_FILE = PUBCHEM_SID_LOG_CSV


def main():
    # The CID-enriched integrated table is read from the output of cid_import.py.
    df_main = pd.read_csv(INTEGRATED_TABLE_CID)

    # With PubChem API extract SIDs only for compounds without a CID.
    # This part creates a log file, that stores the information which string was
    # used to find the SID.
    df_main = map_sids_to_dataframe(df_main)
    df_main["SID"] = df_main["SID"].astype("Int64")
    print(f"PubChem mapping completed. Log file saved to {LOG_FILE}")
    df_main.to_csv(INTEGRATED_TABLE_SID, index=False)
    print(f"Integrated table with SIDs saved to {INTEGRATED_TABLE_SID}")
    log_summary()
    print(f"Summary of PubChem mapping saved to {PUBCHEM_SID_LOG_TXT}")
    return 0



def ask_api_for_sid(compound_name: str) -> tuple[int, str]:
    """Ask the PubChem API for the SID of a compound name."""
    try:
        time.sleep(0.25)
        substance = pubchempy.get_substances(compound_name, "name")
        if substance:
            return substance[0].sid, compound_name
        return None, compound_name
    except Exception as e:
        print(f"Error while fetching SID for {compound_name}: {e}")
        print("Retrying after 1 second...")
        time.sleep(1)
        try:
            substance = pubchempy.get_substances(compound_name, "name")
            if substance:
                print(f"Successfully fetched SID for {compound_name} on retry.")
                return substance[0].sid, compound_name
            print(f"No SID found for {compound_name} on retry.")
            return None, compound_name
        except Exception as e:
            print(f"Error while fetching SID for {compound_name} on retry: {e}")
        return None, compound_name


def get_sid_from_pubchem(compound_names: list[str]) -> tuple[int, str, bool]:
    """Get an SID from PubChem using generated compound-name permutations."""
    number_of_permutations = len(compound_names)
    if number_of_permutations == 1:
        sid, final_name = ask_api_for_sid(compound_names[0])
        if sid:
            return sid, final_name, False
        return None, final_name, False

    for i, compound_name in enumerate(compound_names):
        sid, final_name = ask_api_for_sid(compound_name)
        if sid:
            last_resort = i == number_of_permutations - 1
            return sid, final_name, last_resort

    return None, "SID not found", False


def map_sids_to_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Map SIDs only for rows whose CID is missing."""
    if "CID" not in df.columns:
        raise ValueError("The input DataFrame must contain a CID column.")

    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write(
            "Tracer_ID,Compound_Name_used_to_find_SID,SID,"
            "Nuclide_cleaved_off,Permutations\n"
        )

    tracers_without_cid = df.loc[df["CID"].isna(), "Tracer_ID"].dropna().unique()
    sids = {}
    for tracer in tracers_without_cid:
        compound_names = generate_permutations(tracer)
        sid, final_name, last_resort = get_sid_from_pubchem(compound_names)
        sids[tracer] = sid
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(
                f"{tracer},{final_name},{sid},{last_resort},"
                f"{';'.join(compound_names)}\n"
            )

    if "SID" not in df.columns:
        df["SID"] = pd.NA
    missing_cid = df["CID"].isna()
    df.loc[missing_cid, "SID"] = df.loc[missing_cid, "Tracer_ID"].map(sids)
    return df


def log_summary(path: Path = PUBCHEM_SID_LOG_TXT) -> None:
    """Write a summary of the detailed SID mapping log."""
    df_log = pd.read_csv(LOG_FILE)
    total_tracers = len(df_log)
    tracers_with_sid = df_log["SID"].notna().sum()
    tracers_with_last_resort = df_log["Nuclide_cleaved_off"].sum()
    percentage_with_sid = (
        tracers_with_sid / total_tracers * 100 if total_tracers else 0
    )

    with open(path, "w", encoding="utf-8") as f:
        f.write(f"Total tracers processed: {total_tracers}\n")
        f.write(
            f"Tracers with SID found: {tracers_with_sid} "
            f"({percentage_with_sid:.2f}%)\n"
        )
        f.write(
            f"For following tracers ({tracers_with_last_resort}) SID was found "
            "only after removing the nuclide from the compound name:\n"
        )
        for _, row in df_log[df_log["Nuclide_cleaved_off"] == True].iterrows():
            f.write(f" - {row['Tracer_ID']}\n")


if __name__ == "__main__":
    main()
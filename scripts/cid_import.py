import re
import time
import pandas as pd
import pubchempy

try:
    from .config import *
except ImportError:
    from config import *


LOG_FILE = PUBCHEM_CID_LOG_CSV


def main():
    # The integrated table is read from the output of parse_html.py.
    df_main = pd.read_csv(INTEGRATED_TABLE)

    # With PubChem API extract CIDs for the compounds, that have it available.
    # This part creates a log file, that stores the information which string was
    # used to find the CID.
    df_main = map_cids_to_dataframe(df_main)
    df_main["CID"] = df_main["CID"].astype(
        "Int64"
    )  # Convert PubChem ID to Int64 to allow for NaN values.
    print(f"PubChem mapping completed. Log file saved to {LOG_FILE}")
    df_main.to_csv(INTEGRATED_TABLE_CID, index=False)
    print(f"Integrated table with CIDs saved to {INTEGRATED_TABLE_CID}")
    log_summary()
    print(f"Summary of PubChem mapping saved to {PUBCHEM_CID_LOG_TXT}")
    return 0


# PubChem API uses () instead of [] for nuclides, so the brackets are replaced
# with braces.
def remove_brackets_from_compound_names(compound_name: str) -> str:
    """
    Removes brackets from the compound name.
    Args:
        compound_name: A compound name.
    Returns:
        A compound name with brackets [] replaced with braces ().
    """
    compound_name = compound_name.replace("[", "(", 1).replace("]", ")", 1)
    return compound_name


# Generating permutations of compound names for PubChem API search.
def generate_permutations(compound_name: str) -> list[str]:
    """
    Generates permutations of the compound name to improve the chances of finding
    a match in the PubChem database.
    """
    permutations = []
    compound_name = remove_brackets_from_compound_names(compound_name)
    permutations.append(compound_name)

    # Extract the nuclide and the rest of the compound name using regex.
    match = re.match(r"^\((\d+m?[A-Za-z]+)\)-?(.*)$", compound_name)
    if match:
        nuclide = match.group(1)
        core = match.group(2).lstrip(" -_")

        isotope_match = re.match(r"^(\d+m?)([A-Za-z]+)$", nuclide)
        mass_number = isotope_match.group(1)
        element_symbol = isotope_match.group(2)
        inverted_nuclide = f"{element_symbol}{mass_number}"
        inverted_nuclide_with_space = f"{element_symbol} {mass_number}"
        inverted_nuclide_with_dash = f"{element_symbol}-{mass_number}"
        core_with_removed_nuclide = core.lstrip(element_symbol).lstrip(" -_")
    else:
        return permutations

    permutations.append(f"{nuclide}-{core}")
    permutations.append(f"{nuclide} {core}")
    permutations.append(f"{core} {nuclide}")
    permutations.append(f"{core} ({nuclide})")
    permutations.append(f"[{core}] {inverted_nuclide}")
    permutations.append(f"{core} {inverted_nuclide}")
    permutations.append(f"{core} ({inverted_nuclide})")
    permutations.append(f"{core} {inverted_nuclide_with_space}")
    permutations.append(f"{core} {inverted_nuclide_with_dash}")

    permutations.append(f"{nuclide} {core_with_removed_nuclide}")
    permutations.append(f"{nuclide}-{core_with_removed_nuclide}")
    permutations.append(f"{core_with_removed_nuclide} {nuclide}")
    permutations.append(f"{core_with_removed_nuclide} ({nuclide})")
    permutations.append(f"{core_with_removed_nuclide} {inverted_nuclide}")
    permutations.append(f"{core_with_removed_nuclide} ({inverted_nuclide})")
    permutations.append(f"{core_with_removed_nuclide} {inverted_nuclide_with_space}")
    permutations.append(f"{core_with_removed_nuclide} {inverted_nuclide_with_dash}")

    # Some additional permutations for specific cases.
    if "·H2O" in core:
        core = core.replace("·H2O", "").strip()
        permutations.append(f"({mass_number}){core}")
    if "DOTA-TATE" in core:
        core_with_removed_nuclide = core_with_removed_nuclide.replace(
            "DOTA-TATE", "DOTATATE"
        ).strip()
        permutations.append(f"{nuclide}-{core_with_removed_nuclide}")

    if "Tc" in nuclide:
        permutations.append(f"Technetium ({nuclide}) {core_with_removed_nuclide}")
        permutations.append(f"{inverted_nuclide_with_dash.replace('Tc', 'Technetium')} {core}")
        permutations.append(f"Technetium-{nuclide}-{core_with_removed_nuclide}")
        "Technetium tc 99m succimer"
        permutations.append(f"Technetium {inverted_nuclide_with_space} {core}")


    permutations.append(core)
    return permutations


# Function to ask PubChem API for the CID of a given compound name.
def ask_api_for_cid(compound_name: str) -> tuple[int, str]:
    """
    Asks the PubChem API for the CID of a given compound name.
    """
    try:
        time.sleep(0.25)  # To avoid hitting the API rate limit.
        compound = pubchempy.get_compounds(compound_name, "name")
        if compound:
            return compound[0].cid, compound_name
        return None, compound_name
    except Exception as e:
        print(f"Error while fetching CID for {compound_name}: {e}")
        print("Retrying after 1 second...")
        time.sleep(1)
        try:
            compound = pubchempy.get_compounds(compound_name, "name")
            if compound:
                print(f"Successfully fetched CID for {compound_name} on retry.")
                return compound[0].cid, compound_name
            print(f"No CID found for {compound_name} on retry.")
            return None, compound_name
        except Exception as e:
            print(f"Error while fetching CID for {compound_name} on retry: {e}")
        return None, compound_name


# Extraction of CID.
def get_cid_from_pubchem(compound_names: list[str]) -> tuple[int, str, bool]:
    """
    Gets the CID from PubChem for a list of generated compound-name permutations.
    """
    number_of_permutations = len(compound_names)
    if number_of_permutations == 1:
        cid, final_name = ask_api_for_cid(compound_names[0])
        if cid:
            return cid, final_name, False
        return None, final_name, False

    for i, compound_name in enumerate(compound_names):
        cid, final_name = ask_api_for_cid(compound_name)
        if cid:
            last_resort = i == number_of_permutations - 1
            return cid, final_name, last_resort

    return None, "CID not found", False


# Mapping of CIDs to the main DataFrame.
def map_cids_to_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Maps CIDs to the DataFrame based on the Tracer_ID column.
    """
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write(
            "Tracer_ID,Compound_Name_used_to_find_CID,CID,"
            "Nuclide_cleaved_off,Permutations\n"
        )

    unique_tracers = df["Tracer_ID"].dropna().unique()
    cids = {}
    for tracer in unique_tracers:
        compound_names = generate_permutations(tracer)
        cid, final_name, last_resort = get_cid_from_pubchem(compound_names)
        cids[tracer] = cid
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(
                f"{tracer},{final_name},{cid},{last_resort},"
                f"{';'.join(compound_names)}\n"
            )

    df["CID"] = df["Tracer_ID"].map(cids)
    return df

def log_summary(path: Path = PUBCHEM_CID_LOG_TXT) -> None:
    """
    A short summary of the detailed log file, that is created during the CID mapping.
    """
    df_log = pd.read_csv(LOG_FILE)
    total_tracers = len(df_log)
    tracers_with_cid = df_log["CID"].notna().sum()
    tracers_with_last_resort = df_log["Nuclide_cleaved_off"].sum()

    with open(path, "w", encoding="utf-8") as f:
        f.write(f"Total tracers processed: {total_tracers}\n")
        f.write(f"Tracers with CID found: {tracers_with_cid} ({tracers_with_cid / total_tracers * 100:.2f}%)\n")
        f.write(f"For following tracers ({tracers_with_last_resort}) CID was found only after removing the nuclide from the compound name:\n")
        for _, row in df_log[df_log["Nuclide_cleaved_off"] == True].iterrows():
            f.write(f" - {row['Tracer_ID']}\n")

if __name__ == "__main__":
    main()
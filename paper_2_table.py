# All used radiopharmaceuticals are extracted from these two tables:
# https://www.nature.com/articles/s41392-024-02041-6/tables/2 (approved diagnostic radiopharmaceuticals)
# https://www.nature.com/articles/s41392-024-02041-6/tables/4 (investigational radiopharmaceuticals)
# For proper execution, the HTML content of the tables must be downloaded manually and saved as .htm files in the data/raw folder.
# The files must be named "table_2.htm" and "table_4.htm", respectively.

import pandas as pd
import re
from bs4 import BeautifulSoup
import io
from pathlib import Path
import pubchempy
import time
import mygene # The import is currently unused but may be used to translate protein names to UniProt and NCBI Gene IDs in the future.

# The HTML content of the tables must be obtained from the provided URLs.
# Because the Nature website is protected from automated scraping, the HTML content must be downloaded manually
# and saved as .htm files in the data/raw folder.
# The files are expected to be named "table_2.htm" and "table_4.htm", respectively.

TABLE_2 = Path("data/raw/table_2.htm")
TABLE_4 = Path("data/raw/table_4.htm")
INTEGRATED_TABLE_OUTPUT = Path("data/intermediate/integrated_table.csv")
LOG_FILE = Path("data/intermediate/pubchem_log.csv")

COLUMNS = [
    "Tracer_ID", # The format is [nuclide]molecule_name.
    "Synonyms", # Synonyms are separated by semicolons.
    "Type", # The molecule type is specified (small molecule, peptide, antibody, etc.).
    "Pubchem_ID", # The PubChem ID is specified when available.
    "Modality", # The imaging modality is specified (PET, SPECT).
    "Radionuclide_ID", # The radionuclide ID is specified (e.g., 18F, 11C, etc.).
    "Evidence Level", # The evidence level is scaled from 4 (weakest) to 1 (strongest).
    "Target protein_ID", # The UniProt ID for the target protein is specified.
    "Target gene_ID", # The NCBI Gene ID for the target gene is specified.
    "Disease_ID", # The disease database has not yet been selected (MONDO suggested).
    "Disease name", # The disease associated with the tracer is specified.
    "Target_species", # Scientific names of the target species are used (e.g., Homo sapiens, Mus musculus, etc.). Non-human species only appear in the table with the weakest evidence.
    "Source (URL)", # The source URL
    "Mechanism", # The mechanism of action is described (e.g., receptor binding, enzyme inhibition, etc.).
    "Year", # The publication year is used for duplicate removal and prioritization. In downstream processing.
]
PET_RADIONUCLIDES = ["18F", "68Ga", "11C", "64Cu", "82Rb", "89Zr", "13N",]
SPECT_RADIONUCLIDES = ["99mTc", "111In", "123I", "125I", "201Tl", "67Ga",]
THERAPEUTIC_RADIONUCLIDES = ["177Lu", "90Y", "131I",]

def main():
    # The tables are fetched from the HTML files.
    tables = fetch_table_2(TABLE_2), fetch_table_4(TABLE_4)
    # The two tables are integrated into a single DataFrame with the specified columns.
    df_main = integrate_tables(tables)

    # With Pubchem API extract CIDs for the compounds, that have it available.
    # This part creates a log file, that stores the information which string was used to find the CID.
    df_main = map_cids_to_dataframe(df_main)
    df_main["Pubchem_ID"] = df_main["Pubchem_ID"].astype("Int64")  # Convert Pubchem_ID to Int64 to allow for NaN values.
    print(f"PubChem mapping completed. Log file saved to {LOG_FILE}")
    df_main.to_csv(INTEGRATED_TABLE_OUTPUT, index=False)
    print(f"Integrated table saved to {INTEGRATED_TABLE_OUTPUT}")

    return 0


def fetch_table_2(path: Path) -> pd.DataFrame:
    """
    Fetches the data from the HTML file and returns it as a pandas DataFrame.

    """
    try:
        html_content = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"File not found: {path}\nPlease make sure the HTML file is downloaded and saved in the data/raw directory.\nhttps://www.nature.com/articles/s41392-024-02041-6/tables/2")

    # Only the last table in the HTML content is selected.
    soup = BeautifulSoup(html_content, "html.parser")
    soup = soup.select_one("table.data.last-table")
    # The BeautifulSoup object is converted back to a string so that the table can be read by pandas.
    # StringIO is then used to create a file-like object.
    df = pd.read_html(io.StringIO(str(soup)))[0]
    # All instances of "--" are replaced with NaN values for improved data handling.
    df.replace(to_replace="--", value=pd.NA, inplace=True)
    return df

def fetch_table_4(path: Path) -> pd.DataFrame:
    """
    Fetches the data from the HTML file and returns it as a pandas DataFrame.
    """
    try:
        html_content = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"File not found: {path}\nPlease make sure the HTML file is downloaded and saved in the data/raw directory.\nhttps://www.nature.com/articles/s41392-024-02041-6/tables/4")

    # Only the last table in the HTML content is selected.
    soup = BeautifulSoup(html_content, "html.parser")
    soup = soup.select_one("table.data.last-table")
    # The BeautifulSoup object is converted back to a string so that the table can be read by pandas.
    # StringIO is then used to create a file-like object.
    df = pd.read_html(io.StringIO(str(soup)))[0]
    return df

def integrate_tables(tables: list[pd.DataFrame]) -> pd.DataFrame:
    """
    Integrate the two tables into a single DataFrame with the specified columns.
    arguments:
        tables: A list containing the two DataFrames to be integrated.
    returns:
        A single DataFrame containing the integrated data from both tables.
    """

    # The main DataFrame is created with the specified columns.
    df_main = pd.DataFrame(columns=COLUMNS)

    ### Table 2: Approved Diagnostic Radiopharmaceuticals
    # The PET and SPECT names are extracted from the table.
    table_2 = tables[0]
    pet_names = table_2["PET"].dropna().tolist()
    spect_names = table_2["SPECT"].dropna().tolist()

    # Entries are created and populated with the available information. The remaining columns are filled with NaN values.
    new_pet = pd.DataFrame({
        "Tracer_ID": pet_names,
        "Modality": "PET",
    })

    new_spect = pd.DataFrame({
        "Tracer_ID": spect_names,
        "Modality": "SPECT",
    })

    # The created entries are merged into the main DataFrame.
    df_main = pd.concat([df_main, new_pet, new_spect], ignore_index=True)

    # The synonyms are extracted from the names and saved to the Synonyms column.
    df_main["Synonyms"] = df_main["Tracer_ID"].str.extract(r"\s*\((.*?)\)", expand=False)
    df_main["Tracer_ID"] = df_main["Tracer_ID"].str.replace(r"\s*\(.*?\)", "", regex=True).str.strip()


    ### Table 4: Investigational Radiopharmaceuticals
    table_4 = tables[1]
    column_mapping = {
        "Agent": "Tracer_ID",
        "Agent Type": "Type",
        "Target": "Target protein_ID",
    }

    # The columns in table_4 have different names but correspond to the same information as in the main DataFrame.
    # They are renamed to match the main DataFrame's columns.
    table_4.columns = table_4.columns.str.strip()
    table_4 = table_4[list(column_mapping.keys())].rename(columns=column_mapping)
    df_main = pd.concat([df_main, table_4], ignore_index=True)


    # The entries in Type are converted to lowercase.
    df_main["Type"] = df_main["Type"].str.lower()
    df_main = expand_multi_nuclide_rows(df_main, col_name="Tracer_ID")

    # The radionuclide information is extracted from Tracer_ID and saved to Radionuclide_ID.
    df_main["Radionuclide_ID"] = df_main["Tracer_ID"].str.extract(r"\[(.*?)\]", expand=False)
    # Entries with purely therapeutic radionuclides are removed from the main DataFrame.
    mask = df_main["Radionuclide_ID"].isin(THERAPEUTIC_RADIONUCLIDES)
    df_main = df_main[~mask].reset_index(drop=True)

    # The Modality column is populated based on Radionuclide_ID.
    df_main["Modality"] = df_main.apply(determine_modality, axis=1)

    # At this point there is no point in having duplicate entries in the main DataFrame, so they are removed.
    df_main.drop_duplicates(subset=["Tracer_ID"], inplace=True, ignore_index=True)
    return df_main

# The modality is determined by the nuclide and the Radionuclide_ID.
# If a radionuclide is not included in PET_RADIONUCLIDES or SPECT_RADIONUCLIDES,
# an error is raised so that it can be added to the appropriate list.
def determine_modality(row: pd.Series) -> str:
    """
    Determines the imaging modality (PET or SPECT) based on the radionuclide ID.
    If the radionuclide is not recognized, a ValueError is raised.
    Args:
        row: A pandas Series representing a row in the DataFrame, which must contain the 'Radionuclide_ID' column.
    Returns:
        The imaging modality as a string ("PET" or "SPECT").
    """
    if row["Radionuclide_ID"] in PET_RADIONUCLIDES:
        return "PET"
    elif row["Radionuclide_ID"] in SPECT_RADIONUCLIDES:
        return "SPECT"
    else:
        raise ValueError(f"Unknown radionuclide: {row['Radionuclide_ID']}. Please add it to the PET_RADIONUCLIDES or SPECT_RADIONUCLIDES lists.")

### The following two functions were generated to handle typographical errors in the Tracer_ID column,
# specifically in the twelve rows where "/" notation is used.
def parse_multi_nuclide_tracer(tracer_str: str) -> list[str]:
  """
  Parses a multi-nuclide tracer string (separated by '/') into a list of
  individual standardized tracer names. Fixes common editorial typos found in
  Nature tables.

  Args:
      tracer_str: Raw string from the 'Tracer_ID' / 'Agent' column.
  """
  # The value is converted to a string and leading/trailing whitespace is removed.
  s = str(tracer_str).strip()

  # If no slash is present, the string is returned as a single-element list.
  if "/" not in s:
    return [s]

  # -------------------------------------------------------------------------
  # STEP 1: Editorial typos in the raw HTML text are fixed.
  # -------------------------------------------------------------------------
  # Case 59 is fixed: '[177Lu]/Lu-FAP-2286' -> '[177Lu]Lu-FAP-2286'.
  # The accidental slash between the bracketed isotope and metal symbol is removed.
  s = re.sub(r"\[(\d+[A-Za-z]+)\]/([A-Za-z]+)", r"[\1]\2", s)

  # Case 67 is fixed: '[68Ga]Ga/[177Lu]Lu/-LM3' -> '[68Ga]Ga/[177Lu]Lu-LM3'.
  # The accidental slash before the hyphen is removed.
  s = re.sub(r"/\s*-", "-", s)

  # -------------------------------------------------------------------------
  # STEP 2: The isotope prefixes and core molecule name are separated.
  # -------------------------------------------------------------------------
  # In all twelve cases, the slash '/' appears only in the isotope prefix section.
  # The core ligand name always starts at the first hyphen '-' in the string
  # (e.g., '-FAP-2286', '-PSMA-I&T', '-rhPSMA-7.3', '-DOTA-TATE', '-3BP-227').
  if "-" not in s:
    # If no hyphen is present, the fallback is used.
    return [part.strip() for part in s.split("/") if part.strip()]

  # The string is split at the first hyphen only (maxsplit=1).
  # For example, for '[68Ga]Ga/[177Lu]Lu-PSMA-I&T':
  # prefix_part = '[68Ga]Ga/[177Lu]Lu'
  # ligand_core = 'PSMA-I&T'
  prefix_part, ligand_core = s.split("-", 1)

  # The prefix section is split by '/' to obtain individual isotope prefixes.
  # For example: ['[68Ga]Ga', '[177Lu]Lu']
  prefixes = [p.strip() for p in prefix_part.split("/") if p.strip()]

  # -------------------------------------------------------------------------
  # STEP 3: Full individual tracer names are reconstructed.
  # -------------------------------------------------------------------------
  expanded_tracers = []
  for prefix in prefixes:
    # Case 64 is handled: '[18F]/[177Lu]Lu-rhPSMA-7.3'.
    # '[18F]' is a covalent non-metal label (often written as '[18F]rhPSMA-7.3'
    # or '[18F]-rhPSMA-7.3'), whereas metals have the element symbol outside brackets,
    # as in '[68Ga]Ga-FAP-2286'. The hyphen is retained for consistency.
    full_tracer_name = f"{prefix}-{ligand_core}"
    expanded_tracers.append(full_tracer_name)

  return expanded_tracers
def expand_multi_nuclide_rows(
    df: pd.DataFrame, col_name: str = "Tracer_ID"
) -> pd.DataFrame:
  """
  Splits rows containing multi-nuclide strings in `col_name` into separate rows.
  Automatically duplicates all values from the remaining columns for each newly
  created row.
  """
  # A copy is used to avoid SettingWithCopyWarning in pandas.
  df_out = df.copy()

  # 1. Each string in the target column is transformed into a Python list of tracer names.
  df_out[col_name] = df_out[col_name].apply(parse_multi_nuclide_tracer)

  # 2. The column is expanded with pandas .explode().
  # A new row is created for each list element, and the remaining column values are copied.
  df_out = df_out.explode(col_name, ignore_index=True)

  # 3. Rows with completely filtered-out tracers are dropped.
  df_out = df_out.dropna(subset=[col_name]).reset_index(drop=True)

  return df_out

# Pubchem API uses () instead of [] for nuclides, so the brackets are replaced with braces.
def remove_brackets_from_compound_names(compound_name:str) -> str:
    """
    Removes brackets from the compound names in the list.
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
    Generates permutations of the compound name to improve the chances of finding a match in PubChem.
    Args:
        compound_name: A compound name.
    Returns:
        A list of permutations of the compound name and nuclide.
        If the compound name does not start with a nuclide, 
        the original name is returned as the only permutation.
    """
    permutations = []
    # Remove brackets and replace them with braces.
    compound_name = remove_brackets_from_compound_names(compound_name)
    permutations.append(compound_name)

    # Extract the nuclide and the rest of the compound name using regex.
    # This will return None if the compound does not start with "("
    # Also recognizes m99Tc
    match = re.match(r"^\((\d+m?[A-Za-z]+)\)-?(.*)$", compound_name)
    if match:
        nuclide = match.group(1)
        core = match.group(2).lstrip(" -_") # Remove leading connectors if present.

        # Splitting the mass number and the element symbol for the nuclide.
        isotope_match = re.match(r"^(\d+m?)([A-Za-z]+)$", nuclide)
        mass_number = isotope_match.group(1)
        element_symbol = isotope_match.group(2)
        inverted_nuclide = f"{element_symbol}{mass_number}"
        inverted_nuclide_with_space = f"{element_symbol} {mass_number}"
        inverted_nuclide_with_dash = f"{element_symbol}-{mass_number}"
        core_with_removed_nuclide = core.lstrip(element_symbol).lstrip(" -_")  # Remove the nuclide from the beginning of the compound name.
    else:
        # If the compound does not start with a nuclide, return the original name as the only permutation.
        return permutations

    # The dash notation for the nuclide.
    # e.g., 68Ga-Gallium citrate
    permutations.append(f"{nuclide}-{core}")
    # The space notation for the nuclide.
    # e.g., 68Ga Gallium citrate
    permutations.append(f"{nuclide} {core}")
    # The nuclide at the end of the compound name.
    # e.g., Gallium citrate 68Ga
    permutations.append(f"{core} {nuclide}")
    # The nuclide in parentheses at the end of the compound name.
    # e.g., Gallium citrate (68Ga)
    permutations.append(f"{core} ({nuclide})")
    # The inverted nuclide notation.
    # e.g., Gallium citrate Ga68
    permutations.append(f"{core} {inverted_nuclide}")
    # The inverted nuclide notation with parentheses.
    # e.g., Gallium citrate (Ga68)
    permutations.append(f"{core} ({inverted_nuclide})")
    # The inverted nuclide notation with space.
    # e.g., Gallium citrate Ga 68
    permutations.append(f"{core} {inverted_nuclide_with_space}")
    # The inverted nuclide notation with dash.
    # e.g., Gallium citrate Ga-68
    permutations.append(f"{core} {inverted_nuclide_with_dash}")

    # For some compounds, nuclide, especially metalls like Ga or Cu, can be written twice, like this:
    # [68Ga]Ga-FAPI-04
    # In this case, we can also try to remove the nuclide from the beginning
    # and see if PubChem can find the compound without it.

    # For this purpose, another round of permutations on example [68Ga]Ga-FAPI-04:
    # 68Ga FAPI-04
    permutations.append(f"{nuclide} {core_with_removed_nuclide}")
    # 68Ga-FAPI-04
    permutations.append(f"{nuclide}-{core_with_removed_nuclide}")
    # FAPI-04 68Ga
    permutations.append(f"{core_with_removed_nuclide} {nuclide}")
    # FAPI-04 (68Ga)
    permutations.append(f"{core_with_removed_nuclide} ({nuclide})")
    # FAPI-04 Ga68
    permutations.append(f"{core_with_removed_nuclide} {inverted_nuclide}")
    # FAPI-04 (Ga68)
    permutations.append(f"{core_with_removed_nuclide} ({inverted_nuclide})")
    # FAPI-04 Ga 68
    permutations.append(f"{core_with_removed_nuclide} {inverted_nuclide_with_space}")
    # FAPI-04 Ga-68
    permutations.append(f"{core_with_removed_nuclide} {inverted_nuclide_with_dash}")

    # Last resort: Remove the nuclide entirely and try to find the compound.
    permutations.append(core)

    return permutations

# Function to ask PubChem API for the CID of a given compound name.
def ask_api_for_cid(compound_name: str) -> tuple[int, str]:
    """
    Asks the PubChem API for the CID of a given compound name.
    Args:
        compound_name: A compound name.
    Returns:
        The CID of the compound.
        The final compound name used to find the CID.
    """
    try:
        time.sleep(0.25)  # To avoid hitting the API rate limit.
        compound = pubchempy.get_compounds(compound_name, 'name')
        if compound:
            return compound[0].cid, compound_name
        else:
            return None, compound_name
    except Exception as e:
        print(f"Error while fetching CID for {compound_name}: {e}")
        return None, compound_name

# Extraction of CID.
def get_cid_from_pubchem(compound_names:list[str]) -> tuple[int, str, bool]:
    """
    Gets the CID from PubChem for a given list of compound names. 
    The function iterates through the list of compound names, which are generated permutations of the original compound name,
      to find the CID. If the CID is not found in any of the permutations, it returns None.
    Args:
        compound_names: A list of compound names.
    Returns:
        int: The CID of the compound.
        str: The final compound name used to find the CID.
        bool: True if the CID was found by removing the nuclide, False otherwise.
    """
    number_of_permutations = len(compound_names)
    if number_of_permutations == 1:
        cid, final_name = ask_api_for_cid(compound_names[0])
        if cid:
            return cid, final_name, False
        else:
            return None, final_name, False

    for i, compound_name in enumerate(compound_names):
        cid, final_name = ask_api_for_cid(compound_name)
        if cid:
            last_resort = (i == number_of_permutations - 1)  # True if this is the last permutation (nuclide removed).
            return cid, final_name, last_resort

    return None, "CID not found", False  # If no CID is found in any of the permutations.

# Mapping of CIDs to the main DataFrame.
def map_cids_to_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Maps the CIDs to the main DataFrame based on the Tracer_ID column.
    Args:
        df: The main DataFrame containing the Tracer_ID column.
    Returns:
        The updated DataFrame with the Pubchem_ID column populated.
    """
    # Open the log file and write the header.
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("Tracer_ID,Compound_Name_used_to_find_CID,CID,Nuclide_cleaved_off,Permutations\n")

    unique_tracers = df["Tracer_ID"].dropna().unique()
    cids = {}
    for index, tracer in enumerate(unique_tracers):
        compound_names = generate_permutations(tracer)
        cid, final_name, last_resort = get_cid_from_pubchem(compound_names)
        cids[tracer] = cid
        # Log the results to the log file.
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{tracer},{final_name},{cid},{last_resort},{';'.join(compound_names)}\n")

    # Map the CIDs to the DataFrame.
    df["Pubchem_ID"] = df["Tracer_ID"].map(cids)
    return df

    
if __name__ == "__main__":
    main()

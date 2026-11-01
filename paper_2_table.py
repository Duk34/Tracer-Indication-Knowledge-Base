# This script aims to extract all the used Radiopharmaceuticals from these two tables:
# https://www.nature.com/articles/s41392-024-02041-6/tables/2 (approved diagnostic radiopharmaceuticals)
# https://www.nature.com/articles/s41392-024-02041-6/tables/4 (investigational radiopharmaceuticals)
# For this script to work properly, the HTML content of the tables must be downloaded manually and saved as .htm files in the data/raw folder.

import pandas as pd
import re
from bs4 import BeautifulSoup
import io
#import mygene # not used yet, might be helpful to translate the protein names to uniProt IDs and NCBI Gene IDs in the future.

# First things first, we need to get the HTML content of the tables from the provided URLs. 
# Nature website is protected from automated scraping, since we are only dealing with two tables,
# we can manually download the HTML content of the tables and save them as .html files in the data/raw folder.
# The files were saved as "table_2.html" and "table_4.html" respectively.

TABLE_2 = "data/raw/table_2.htm"
TABLE_4 = "data/raw/table_4.htm"
COLUMNS = [
    "Tracer_ID", # [nuclide]molecule_name
    "Synonyms", # Synonyms separated by semicolons
    "Type", # Molecule type (small molecule, peptide, antibody, etc.)
    "Pubchem_ID", # PubChem ID for the molecule (optional)
    "Modality", # Imaging modality (PET, SPECT, etc.)
    "Radionuclide_ID", # Radionuclide ID (e.g., 18F, 11C, etc.)
    "Evidence Level", # Scale from 1 to 4 indicating the level of evidence supporting the tracer's use
    "Target protein_ID", # UniProt ID for the target protein
    "Target gene_ID", # NCBI Gene ID for the target gene
    "Disease_ID", # Not decided yet, which database to use for disease IDs (e.g., MeSH, OMIM, etc.)
    "Disease name", # Name of the disease associated with the tracer
    "Target_species", # Species of the target protein (e.g., human, mouse, etc.)
    "Source (URL)", # URL to the source of the information (e.g., PubMed, company website, etc.)
    "Mechanism", # Description of the mechanism of action of the tracer (e.g., binding to a specific receptor, enzyme inhibition, etc.)
    "Year", # Year - how old is this particular entry, for removing duplicates and prioritizing newer entries in the future.
]
PET_RADIONUCLIDES = ["18F", "68Ga", "11C", "64Cu", "82Rb", "89Zr", "13N",]
SPECT_RADIONUCLIDES = ["99mTc", "111In", "123I", "125I", "201Tl", "67Ga",]
THERAPEUTIC_RADIONUCLIDES = ["177Lu", "90Y", "131I",]

def main():
    # Fetch the tables from the HTML files
    tables = fetch_table_2(TABLE_2), fetch_table_4(TABLE_4)
    # Integrate the two tables into a single DataFrame with the specified columns
    integrate_tables(tables)

    

def fetch_table_2(path):
    with open(path, "r", encoding="utf-8") as f:
        html_content = f.read()

    # Only select the last table in the HTML content, which contains the data we need.
    soup = BeautifulSoup(html_content, "html.parser")
    soup = soup.select_one("table.data.last-table")
    # For pandas to properly read the table, we need to convert the BeautifulSoup object back to a string
    # and then use StringIO to create a file-like object.
    df = pd.read_html(io.StringIO(str(soup)))[0]
    # Replace all instances of "--" with NaN values for better data handling.
    df.replace(to_replace="--", value=pd.NA, inplace=True)
    return df

def fetch_table_4(path):
    with open(path, "r", encoding="utf-8") as f:
        html_content = f.read()

    # Only select the last table in the HTML content, which contains the data we need.
    soup = BeautifulSoup(html_content, "html.parser")
    soup = soup.select_one("table.data.last-table")
    # For pandas to properly read the table, we need to convert the BeautifulSoup object back to a string
    # and then use StringIO to create a file-like object.
    df = pd.read_html(io.StringIO(str(soup)))[0]
    df.to_csv("data/intermediate/table_4.csv", index=False)
    return df

def integrate_tables(tables):
    """
    Integrate the two tables into a single DataFrame with the specified columns.
    """

    # Create the main DataFrame with the specified columns
    df_main = pd.DataFrame(columns=COLUMNS)

    ### Table 2: Approved Diagnostic Radiopharmaceuticals
    # Extract the PET and SPECT names from the table
    table_2 = tables[0]
    pet_names = table_2["PET"].dropna().tolist()
    spect_names = table_2["SPECT"].dropna().tolist()

    # Create entries and fill them with available information. The rest of the columns will be filled with NaN values.
    new_pet = pd.DataFrame({
        "Tracer_ID": pet_names,
        "Modality": "PET",
    })

    new_spect = pd.DataFrame({
        "Tracer_ID": spect_names,
        "Modality": "SPECT",
    })

    # Merge the created entries into the main DataFrame.
    df_main = pd.concat([df_main, new_pet, new_spect], ignore_index=True)

    # Now extract the synonyms from the names and save them to synonyms column.
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
    # We need to rename them to match the main DataFrame's columns.
    table_4.columns = table_4.columns.str.strip()
    table_4 = table_4[list(column_mapping.keys())].rename(columns=column_mapping)
    df_main = pd.concat([df_main, table_4], ignore_index=True)


    # Some cleanup, entries in Type to lowercase.
    df_main["Type"] = df_main["Type"].str.lower()
    df_main = expand_multi_nuclide_rows(df_main, col_name="Tracer_ID")

    # Extract the information about the radionuclide from the Tracer_ID column and save it to the Radionuclide_ID column.
    df_main["Radionuclide_ID"] = df_main["Tracer_ID"].str.extract(r"\[(.*?)\]", expand=False)
    # Remove entries with purely therapeutic radionuclides from the main DataFrame.
    mask = df_main["Radionuclide_ID"].isin(THERAPEUTIC_RADIONUCLIDES)
    df_main = df_main[~mask].reset_index(drop=True)

    # Modality is determined by the radionuclide, so we can fill the Modality column based on the Radionuclide_ID.
    df_main["Modality"] = df_main.apply(determine_modality, axis=1)
    
    df_main.to_csv("data/intermediate/integrated_table.csv", index=False)



# The nuclide determines the modality, so we can fill the Modality column based on the Radionuclide_ID.
# If there is a radionuclide thats not in the PET_RADIONUCLIDES or SPECT_RADIONUCLIDES lists, 
# raise an error to catch it and add it to the lists.
def determine_modality(row):
    if row["Radionuclide_ID"] in PET_RADIONUCLIDES:
        return "PET"
    elif row["Radionuclide_ID"] in SPECT_RADIONUCLIDES:
        return "SPECT"
    else:
        raise ValueError(f"Unknown radionuclide: {row['Radionuclide_ID']}. Please add it to the PET_RADIONUCLIDES or SPECT_RADIONUCLIDES lists.")



### Following 2 functions are AI generated, their purpose is to handle tyopograohical errors in the Tracer_ID column,
# speciffically in those 12 rows, where notation with "/" is used.
def parse_multi_nuclide_tracer(tracer_str: str) -> list[str]:
  """
  Parses a multi-nuclide tracer string (separated by '/') into a list of
  individual standardized tracer names. Fixes common editorial typos found in
  Nature tables.

  Args:
      tracer_str: Raw string from the 'Tracer_ID' / 'Agent' column.
  """
  # Convert to string and strip leading/trailing whitespace
  s = str(tracer_str).strip()

  # Fast path: if there is no slash in the string, return it as a single-element list
  if "/" not in s:
    return [s]

  # -------------------------------------------------------------------------
  # STEP 1: Fix editorial typos in the raw HTML text
  # -------------------------------------------------------------------------
  # Fix Case 59: '[177Lu]/Lu-FAP-2286' -> '[177Lu]Lu-FAP-2286'
  # (Removes the accidental slash placed between the bracketed isotope and metal symbol)
  s = re.sub(r"\[(\d+[A-Za-z]+)\]/([A-Za-z]+)", r"[\1]\2", s)

  # Fix Case 67: '[68Ga]Ga/[177Lu]Lu/-LM3' -> '[68Ga]Ga/[177Lu]Lu-LM3'
  # (Removes the accidental slash placed right before the hyphen)
  s = re.sub(r"/\s*-", "-", s)

  # -------------------------------------------------------------------------
  # STEP 2: Split into the isotope prefixes part and the core molecule name
  # -------------------------------------------------------------------------
  # In all 12 cases, the slash '/' ONLY appears in the isotope prefix section.
  # The core ligand name ALWAYS starts at the FIRST hyphen '-' in the string
  # (e.g., '-FAP-2286', '-PSMA-I&T', '-rhPSMA-7.3', '-DOTA-TATE', '-3BP-227').
  if "-" not in s:
    # Fallback in case there is no hyphen at all
    return [part.strip() for part in s.split("/") if part.strip()]

  # Split at the FIRST hyphen ONLY (maxsplit=1)
  # Example for '[68Ga]Ga/[177Lu]Lu-PSMA-I&T':
  # prefix_part = '[68Ga]Ga/[177Lu]Lu'
  # ligand_core = 'PSMA-I&T'
  prefix_part, ligand_core = s.split("-", 1)

  # Split the prefix section by '/' to get individual isotope prefixes
  # Example: ['[68Ga]Ga', '[177Lu]Lu']
  prefixes = [p.strip() for p in prefix_part.split("/") if p.strip()]

  # -------------------------------------------------------------------------
  # STEP 3: Reconstruct full individual tracer names
  # -------------------------------------------------------------------------
  expanded_tracers = []
  for prefix in prefixes:
    # Case 64 handling: '[18F]/[177Lu]Lu-rhPSMA-7.3'
    # Notice that '[18F]' is a covalent non-metal label (often written as '[18F]rhPSMA-7.3'
    # or '[18F]-rhPSMA-7.3'), whereas metals have the element symbol outside brackets
    # like '[68Ga]Ga-FAP-2286'. Keeping the hyphen makes it uniform: '[18F]-rhPSMA-7.3'.
    full_tracer_name = f"{prefix}-{ligand_core}"
    expanded_tracers.append(full_tracer_name)

  return expanded_tracers
def expand_multi_nuclide_rows(
    df: pd.DataFrame, col_name: str = "Tracer_ID"
) -> pd.DataFrame:
  """Splits rows containing multi-nuclide strings in `col_name` into separate rows.

  Automatically duplicates all values from the remaining columns for each newly
  created row.
  """
  # Work on a copy to avoid SettingWithCopyWarning in pandas
  df_out = df.copy()

  # 1. Transform each string in the target column into a Python list of tracer names
  df_out[col_name] = df_out[col_name].apply(parse_multi_nuclide_tracer)

  # 2. Use pandas .explode() on the column.
  # .explode() takes a column of lists and creates a new row for each element in the list,
  # automatically copying all other column values (Target, Type, Disease, etc.) to the new rows!
  df_out = df_out.explode(col_name, ignore_index=True)

  # 3. Drop rows where the tracer might have been filtered out completely
  df_out = df_out.dropna(subset=[col_name]).reset_index(drop=True)

  return df_out

    
if __name__ == "__main__":
    main()

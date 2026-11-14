# Configuration file

from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_RAW_PATH = PROJECT_ROOT / "data" / "raw"
DATA_INTERMEDIATE_PATH = PROJECT_ROOT / "data" / "intermediate"
DATA_PROCESSED_PATH = PROJECT_ROOT / "data" / "processed"

TABLE_2_HTML = DATA_RAW_PATH / "table_2.htm"
TABLE_4_HTML = DATA_RAW_PATH / "table_4.htm"
TABLE_2_CSV = DATA_INTERMEDIATE_PATH / "table_2.csv"
TABLE_4_CSV = DATA_INTERMEDIATE_PATH / "table_4.csv"
INTEGRATED_TABLE = DATA_INTERMEDIATE_PATH / "integrated_table.csv"
INTEGRATED_TABLE_CID = DATA_INTERMEDIATE_PATH / "integrated_table_CID.csv"
INTEGRATED_TABLE_SID = DATA_INTERMEDIATE_PATH / "integrated_table_SID.csv"
PUBCHEM_CID_LOG_CSV = DATA_INTERMEDIATE_PATH / "pubchem_CID_log.csv"
PUBCHEM_CID_LOG_TXT = DATA_INTERMEDIATE_PATH / "pubchem_CID_log.txt"
PUBCHEM_SID_LOG_CSV = DATA_INTERMEDIATE_PATH / "pubchem_SID_log.csv"
PUBCHEM_SID_LOG_TXT = DATA_INTERMEDIATE_PATH / "pubchem_SID_log.txt"

# Global variables:
# The columns of the main DF
COLUMNS = [
    "Tracer_ID", # The format is [nuclide]molecule_name.
    "Synonyms", # Synonyms are separated by semicolons.
    "Type", # The molecule type is specified (small molecule, peptide, antibody, etc.).
    "CID", # The PubChem Compound ID (CID) is specified. (if available)
    "SID", # The PubChem Substance ID (SID) is specified. (if available and if the CID is not available)
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
# Radionuclides associated with PET
PET_RADIONUCLIDES = ["18F", "68Ga", "11C", "64Cu", "82Rb", "89Zr", "13N",]
# Radionuclides associated with SPECT
SPECT_RADIONUCLIDES = ["99mTc", "111In", "123I", "125I", "201Tl", "67Ga",]
# Radionuclides not used in diagnostics
THERAPEUTIC_RADIONUCLIDES = ["177Lu", "90Y", "131I",]
# Configuration file

from pathlib import Path

# Paths and URLs
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_RAW_PATH = PROJECT_ROOT / "data" / "raw"
DATA_INTERMEDIATE_PATH = PROJECT_ROOT / "data" / "intermediate"
DATA_PROCESSED_PATH = PROJECT_ROOT / "data" / "processed"

TABLE_2_HTML = DATA_RAW_PATH / "table_2.htm"
TABLE_4_HTML = DATA_RAW_PATH / "table_4.htm"
TABLE_2_CSV = DATA_INTERMEDIATE_PATH / "table_2.csv"
TABLE_4_CSV = DATA_INTERMEDIATE_PATH / "table_4.csv"
INTEGRATED_TABLE = DATA_INTERMEDIATE_PATH / "integrated_table.csv"
INTEGRATED_TABLE_CORRECTED = DATA_INTERMEDIATE_PATH / "integrated_table_corrected.csv"
INTEGRATED_TABLE_CID = DATA_INTERMEDIATE_PATH / "integrated_table_CID.csv"
INTEGRATED_TABLE_SID = DATA_INTERMEDIATE_PATH / "integrated_table_SID.csv"
INTEGRATED_TABLE_SYNONYMS = DATA_INTERMEDIATE_PATH / "integrated_table_synonyms.csv"
INTEGRATED_TABLE_PROTEIN_ID = DATA_INTERMEDIATE_PATH / "integrated_table_protein_id.csv"
INTEGRATED_TABLE_RADIOPHARM = DATA_INTERMEDIATE_PATH / "integrated_table_radiopharm.csv"
INTEGRATED_TABLE_RADIOPHARM_POPULATED = DATA_INTERMEDIATE_PATH / "integrated_table_radiopharm_populated.csv"


PUBCHEM_CID_LOG_CSV = DATA_INTERMEDIATE_PATH / "pubchem_CID_log.csv"
PUBCHEM_CID_LOG_TXT = DATA_INTERMEDIATE_PATH / "pubchem_CID_log.txt"
PUBCHEM_SID_LOG_CSV = DATA_INTERMEDIATE_PATH / "pubchem_SID_log.csv"
PUBCHEM_SID_LOG_TXT = DATA_INTERMEDIATE_PATH / "pubchem_SID_log.txt"

# REST API RadioPharm
RADIOPHARM_API_URL = "https://radiopharm.idrblab.cn/api/radiopharm/postSearchDrugResult"
RADIOPHARM_INFO_API = "https://radiopharm.idrblab.cn/api/radiopharm/getDrugInfo"
RADIOPHARM_DRUG_DESCRIPTION = "https://radiopharm.idrblab.cn/api/radiopharm/getDrugDescription"
RADIOPHARM_TARGET_INFO = "https://radiopharm.idrblab.cn/api/radiopharm/getTarget"

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
# The corrected names of chemicals from the original table
CORRECTED_NAMES = {
    "[99mTc]NaTcO4": "[99mTc]Sodium pertechnetate",
    "[123I]Sodium iodinate": "[123I]Sodium iodide",
    "[99mTc]Tc-DTPA-Tilmanocept": "[99mTc]Tilmanocept",
    "[99mTc]TcECG": "[99mTc]ECG",
    

}

# Fallbacks for target names that MyGene cannot resolve reliably.
# Values are semicolon-separated for protein complexes or several subunits.
TARGET_ID_MAPPING = {
    "AMPAR": {
        "protein": "P42261;P42262;P42263;P48058",
        "gene": "2890;2891;2892;2893",
    },
    "A\u03b2": {
        "protein": "P05067",
        "gene": "351",
    },
    "CB1R/CB2R": {
        "protein": "P21554;P34972",
        "gene": "1268;1281",
    },
    "CD3": {
        "protein": "P04234;P07766;P09693",
        "gene": "915;916;917",
    },
    "CD8": {
        "protein": "P01732;P10966",
        "gene": "925;926",
    },
    "FAP": {
        "protein": "Q12884",
        "gene": "2191",
    },
    "FAAH": {
        "protein": "O00519",
        "gene": "2166",
    },
    "GRPR": {
        "protein": "P30550",
        "gene": "2925",
    },
    "Granzyme B": {
        "protein": "P10144",
        "gene": "3002",
    },
    "IDO": {
        "protein": "P14902",
        "gene": "3620",
    },
    "Integrin": {
        "protein": "P06756;P05106",
        "gene": "3685;3690",
    },
    "MAGL": {
        "protein": "Q99685",
        "gene": "11343",
    },
    "Nectin-4": {
        "protein": "Q96NY8",
        "gene": "81607",
    },
    "NTSR-1": {
        "protein": "P30989",
        "gene": "4914",
    },
    "PD-1": {
        "protein": "Q15116",
        "gene": "5133",
    },
    "PD-L1": {
        "protein": "Q9NZQ7",
        "gene": "29126",
    },
    "PSMA": {
        "protein": "Q04609",
        "gene": "2346",
    },
    "SSTR": {
        "protein": "P30874",
        "gene": "6752",
    },
    "Sigma receptors": {
        "protein": "Q99720",
        "gene": "10280",
    },
    "Tau": {
        "protein": "P10636",
        "gene": "4137",
    },
    "UPAR": {
        "protein": "Q03405",
        "gene": "5329",
    },
    "VMAT2": {
        "protein": "Q05940",
        "gene": "6571",
    },
    "\u03b1-synuclein": {
        "protein": "P37840",
        "gene": "6622",
    },
}
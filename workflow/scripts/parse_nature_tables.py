"""Turn Nature tables 2 (approved) and 4 (investigational) into one tracer table.

Source: Signal Transduct Target Ther 2024, doi:10.1038/s41392-024-02041-6
Run by Snakemake (rule radiopharm_parse_tables), which provides `snakemake.input/output`.
"""

import io
import re

import pandas as pd
from bs4 import BeautifulSoup

# Columns of our curation scheme.
COLUMNS = [
    "Tracer_ID",  # [nuclide]molecule_name
    "Synonyms",  # separated by semicolons
    "Type",  # small molecule, peptide, antibody, ...
    "CID",  # PubChem Compound ID
    "SID",  # PubChem Substance ID (only if there is no CID)
    "Modality",  # PET or SPECT
    "Radionuclide_ID",  # 18F, 11C, ...
    "Evidence Level",  # 4 (strongest) ... 1 (weakest)
    "Target protein_ID",  # UniProt ID
    "Target gene_ID",  # NCBI Gene ID
    "Disease_ID",  # not chosen yet (MONDO suggested)
    "Disease name",
    "Target_species",  # e.g. Homo sapiens
    "Source (URL)",
    "Mechanism",  # receptor binding, enzyme inhibition, ...
    "Year",  # publication year, used for duplicate removal later
]
PET_RADIONUCLIDES = ["18F", "68Ga", "11C", "64Cu", "82Rb", "89Zr", "13N"]
SPECT_RADIONUCLIDES = ["99mTc", "111In", "123I", "125I", "201Tl", "67Ga"]
THERAPEUTIC_RADIONUCLIDES = ["177Lu", "90Y", "131I"]  # not used for imaging

# Names in the Nature tables that PubChem/RadioPharm do not understand.
CORRECTED_NAMES = {
    "[99mTc]NaTcO4": "[99mTc]Sodium pertechnetate",  # formula -> name
    "[123I]Sodium iodinate": "[123I]Sodium iodide",  # wrong name
    "[99mTc]Tc-DTPA-Tilmanocept": "[99mTc]Tilmanocept",  # chelator in the name
    "[99mTc]TcECG": "[99mTc]ECG",
    "[13N]NH3·H2O": "[13N]NH3",
}


def read_html_table(path: str) -> pd.DataFrame:
    """Read the data table of a saved Nature table page."""
    html = open(path, encoding="utf-8").read()
    table = BeautifulSoup(html, "html.parser").select_one("table.data.last-table")
    if table is None:
        raise ValueError(f"No Nature data table found in {path}")
    return pd.read_html(io.StringIO(str(table)))[0].replace("--", pd.NA)


def parse_multi_nuclide_tracer(tracer: object) -> list[str]:
    """ "[68Ga]/[64Cu]-DOTATATE" -> ["[68Ga]-DOTATATE", "[64Cu]-DOTATATE"]"""
    value = str(tracer).strip()
    if "/" not in value:
        return [value]
    value = re.sub(r"\[(\d+[A-Za-z]+)\]/([A-Za-z]+)", r"[\1]\2", value)
    value = re.sub(r"/\s*-", "-", value)
    if "-" not in value:
        return [part.strip() for part in value.split("/") if part.strip()]
    prefix_part, ligand_core = value.split("-", 1)
    prefixes = [prefix.strip() for prefix in prefix_part.split("/") if prefix.strip()]
    return [f"{prefix}-{ligand_core}" for prefix in prefixes]


def determine_modality(radionuclide: str) -> str:
    if radionuclide in PET_RADIONUCLIDES:
        return "PET"
    if radionuclide in SPECT_RADIONUCLIDES:
        return "SPECT"
    raise ValueError(f"Unknown radionuclide: {radionuclide}. Add it to the PET or SPECT list.")


def integrate_tables(table_2: pd.DataFrame, table_4: pd.DataFrame) -> pd.DataFrame:
    # Table 2 has one column per modality, the synonym is in brackets: "[18F]FDG (Fludeoxyglucose)".
    approved = pd.concat(
        [
            pd.DataFrame({"Tracer_ID": table_2["PET"].dropna(), "Modality": "PET"}),
            pd.DataFrame({"Tracer_ID": table_2["SPECT"].dropna(), "Modality": "SPECT"}),
        ],
        ignore_index=True,
    )
    approved["Synonyms"] = approved["Tracer_ID"].str.extract(r"\s*\((.*?)\)", expand=False)
    approved["Tracer_ID"] = approved["Tracer_ID"].str.replace(r"\s*\(.*?\)", "", regex=True).str.strip()

    table_4 = table_4.rename(columns=lambda column: str(column).strip())
    investigational = table_4[["Agent", "Agent Type", "Target"]].rename(
        columns={"Agent": "Tracer_ID", "Agent Type": "Type", "Target": "Target protein_ID"}
    )

    tracers = pd.concat([approved, investigational], ignore_index=True)
    tracers["Type"] = tracers["Type"].str.lower()
    tracers["Tracer_ID"] = tracers["Tracer_ID"].apply(parse_multi_nuclide_tracer)
    tracers = tracers.explode("Tracer_ID", ignore_index=True).dropna(subset=["Tracer_ID"])
    tracers["Radionuclide_ID"] = tracers["Tracer_ID"].str.extract(r"\[(.*?)\]", expand=False)
    tracers = tracers[~tracers["Radionuclide_ID"].isin(THERAPEUTIC_RADIONUCLIDES)]
    tracers["Modality"] = tracers["Radionuclide_ID"].apply(determine_modality)

    tracers = tracers.groupby("Tracer_ID", sort=False, as_index=False).first()
    tracers["Tracer_ID"] = tracers["Tracer_ID"].replace(CORRECTED_NAMES).str.strip()
    return tracers.reindex(columns=COLUMNS)


table_2 = read_html_table(snakemake.input.table_2)
table_4 = read_html_table(snakemake.input.table_4)
integrate_tables(table_2, table_4).to_csv(snakemake.output[0], index=False)

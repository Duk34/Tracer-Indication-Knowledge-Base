"""Parse the Nature HTML tables and create the integrated tracer table."""

from __future__ import annotations

import io
import re
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup

try:
    from .config import *
except ImportError:
    from config import *


TABLE_SELECTOR = "table.data.last-table"
TABLE_2_URL = "https://www.nature.com/articles/s41392-024-02041-6/tables/2"
TABLE_4_URL = "https://www.nature.com/articles/s41392-024-02041-6/tables/4"


def read_html_table(path: Path, source_url: str) -> pd.DataFrame:
    """Read the Nature table selected by ``TABLE_SELECTOR`` from an HTML file."""
    try:
        html_content = path.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise FileNotFoundError(
            f"HTML file not found: {path}. Download the table from {source_url} "
            "and save it at this path."
        ) from error

    table = BeautifulSoup(html_content, "html.parser").select_one(TABLE_SELECTOR)
    if table is None:
        raise ValueError(
            f"No table matching {TABLE_SELECTOR!r} was found in {path}."
        )

    parsed_tables = pd.read_html(io.StringIO(str(table)))
    if not parsed_tables:
        raise ValueError(f"No readable table was found in {path}.")

    return parsed_tables[0].replace("--", pd.NA)


def fetch_table_2(path: Path = TABLE_2_HTML) -> pd.DataFrame:
    """Read the approved diagnostic radiopharmaceuticals table."""
    return read_html_table(path, TABLE_2_URL)


def fetch_table_4(path: Path = TABLE_4_HTML) -> pd.DataFrame:
    """Read the investigational radiopharmaceuticals table."""
    return read_html_table(path, TABLE_4_URL)


def integrate_tables(
    tables: tuple[pd.DataFrame, pd.DataFrame] | list[pd.DataFrame],
) -> pd.DataFrame:
    """Integrate the approved and investigational tracer tables."""
    if len(tables) != 2:
        raise ValueError("Exactly two tables are required: table 2 and table 4.")

    table_2, table_4 = tables
    required_table_2_columns = {"PET", "SPECT"}
    missing_table_2_columns = required_table_2_columns - set(table_2.columns)
    if missing_table_2_columns:
        raise ValueError(
            f"Table 2 is missing required columns: {sorted(missing_table_2_columns)}"
        )

    table_4 = table_4.rename(columns=lambda column: str(column).strip())
    column_mapping = {
        "Agent": "Tracer_ID",
        "Agent Type": "Type",
        "Target": "Target protein_ID",
    }
    missing_table_4_columns = set(column_mapping) - set(table_4.columns)
    if missing_table_4_columns:
        raise ValueError(
            f"Table 4 is missing required columns: {sorted(missing_table_4_columns)}"
        )

    approved = pd.concat(
        [
            pd.DataFrame(
                {"Tracer_ID": table_2["PET"].dropna(), "Modality": "PET"}
            ),
            pd.DataFrame(
                {"Tracer_ID": table_2["SPECT"].dropna(), "Modality": "SPECT"}
            ),
        ],
        ignore_index=True,
    )
    approved["Synonyms"] = approved["Tracer_ID"].str.extract(
        r"\s*\((.*?)\)", expand=False
    )
    approved["Tracer_ID"] = (
        approved["Tracer_ID"].str.replace(r"\s*\(.*?\)", "", regex=True).str.strip()
    )

    investigational = table_4[list(column_mapping)].rename(columns=column_mapping)
    integrated = pd.concat([approved, investigational], ignore_index=True)
    integrated["Type"] = integrated["Type"].str.lower()
    integrated = expand_multi_nuclide_rows(integrated)
    integrated["Radionuclide_ID"] = integrated["Tracer_ID"].str.extract(
        r"\[(.*?)\]", expand=False
    )
    integrated = integrated[
        ~integrated["Radionuclide_ID"].isin(THERAPEUTIC_RADIONUCLIDES)
    ].reset_index(drop=True)
    integrated["Modality"] = integrated.apply(determine_modality, axis=1)

    return (
        integrated.groupby("Tracer_ID", sort=False, as_index=False)
        .first()
        .reindex(columns=COLUMNS)
    )


def determine_modality(row: pd.Series) -> str:
    """Return the imaging modality associated with a radionuclide."""
    radionuclide = row["Radionuclide_ID"]
    if radionuclide in PET_RADIONUCLIDES:
        return "PET"
    if radionuclide in SPECT_RADIONUCLIDES:
        return "SPECT"
    raise ValueError(
        f"Unknown radionuclide: {radionuclide}. Add it to the PET or SPECT list."
    )


def parse_multi_nuclide_tracer(tracer: object) -> list[str]:
    """Expand slash-separated nuclide prefixes into individual tracer names."""
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


def expand_multi_nuclide_rows(
    dataframe: pd.DataFrame, col_name: str = "Tracer_ID"
) -> pd.DataFrame:
    """Split rows containing multiple nuclides into separate rows."""
    expanded = dataframe.copy()
    expanded[col_name] = expanded[col_name].apply(parse_multi_nuclide_tracer)
    return expanded.explode(col_name, ignore_index=True).dropna(subset=[col_name])


def parse_html_tables(
    table_2_path: Path = TABLE_2_HTML,
    table_4_path: Path = TABLE_4_HTML,
    output_path: Path = INTEGRATED_TABLE,
) -> pd.DataFrame:
    """Read both HTML tables, integrate them, and write the resulting CSV."""
    integrated = integrate_tables(
        (fetch_table_2(table_2_path), fetch_table_4(table_4_path))
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    integrated.to_csv(output_path, index=False)
    return integrated


if __name__ == "__main__":
    parse_html_tables()
"""This script fills the column "Target protein_ID" of a main csv file using a second csv file.
The main file needs a column "Synonyms" and "Tracer_ID" whose values are treated as additional synonyms.
The reference file needs "Synonyms" and "Target protein_ID" (all multi-value fields separated by ";").
The synonyms and Tracer_IDs of the main file are compared to the Synonyms (optional: and Tracer_IDs) of the reference file, ignoring case.
If one or more terms match, all matching "Target protein_ID" values from the reference file are collected,
deduplicated, sorted, and written to the main file separated by ";".
Only empty cells are filled; existing values in the main file are never changed.

Use it like this:
python fill_protein_ids_from_reference_table.py main.csv reference.csv [output.csv]

A filename is looked up in data/intermediate. Without an output argument,
<main name>_filled_protein_ids.csv is written next to the main file.

eg. python fill_protein_ids_from_reference_table.py integrated_table_radiopharm_populated.csv imageable_genome_mapped_radionuclides.csv"""

import argparse
from pathlib import Path

import pandas as pd

try:
    from .config import *
except ImportError:
    from config import *


def build_lookup(reference_df: pd.DataFrame) -> dict[str, set[str]]:
    """Map every lower-case Synonyms or Tracer_ID of the reference file to all matching Target protein_IDs."""
    lookup: dict[str, set[str]] = {}
    has_tracer_col = "Tracer_ID" in reference_df.columns

    synonyms_col = reference_df["Synonyms"].fillna("")
    protein_ids_col = reference_df["Target protein_ID"].fillna("")
    tracer_ids_col = reference_df["Tracer_ID"].fillna("") if has_tracer_col else [""] * len(reference_df)

    for synonyms, tracer_ids, protein_ids in zip(synonyms_col, tracer_ids_col, protein_ids_col):
        # Target protein_id needs to be present, otherwise we cannot fill anything
        if not protein_ids.strip():
            continue

        # Either Synonyms OR Tracer_IDs must be present
        if not synonyms.strip() and not tracer_ids.strip():
            continue

        ids = {pid.strip() for pid in protein_ids.split(";") if pid.strip()}
        if not ids:
            continue

        # Collect all search terms from Synonyms and Tracer_IDs, ignoring empty strings
        terms = []
        if synonyms.strip():
            terms.extend(synonyms.split(";"))
        if tracer_ids.strip():
            terms.append(tracer_ids)

        for term in terms:
            key = term.strip().lower()
            if key:
                lookup.setdefault(key, set()).update(ids) #add ids to the set of protein_ids for this key

    return lookup


def fill_protein_ids(main_df: pd.DataFrame, reference_df: pd.DataFrame) -> pd.DataFrame:
    """Fill empty Target protein_ID cells in main_df using matching Synonyms and Tracer_IDs."""
    lookup = build_lookup(reference_df)

    if "Target protein_ID" not in main_df.columns:
        main_df["Target protein_ID"] = pd.Series(pd.NA, index=main_df.index, dtype="string")

    # Only rows without an existing entry are filled
    empty = main_df["Target protein_ID"].fillna("").str.strip() == ""

    n_filled = 0
    for i in main_df.index[empty]:
        search_terms = []

        synonyms = main_df.at[i, "Synonyms"]
        if pd.notna(synonyms):
            search_terms.extend(synonyms.split(";"))

        tracer_ids = main_df.at[i, "Tracer_ID"]
        if pd.notna(tracer_ids):
            search_terms.append(tracer_ids)

        matched_ids = set()
        for term in search_terms:
            ids = lookup.get(term.strip().lower())
            if ids:
                matched_ids.update(ids)

        if matched_ids:
            # Sort IDs for deterministic output and join with ";"
            main_df.at[i, "Target protein_ID"] = ";".join(sorted(matched_ids))
            n_filled += 1

    print(f"Filled {n_filled} of {empty.sum()} empty Target protein_ID cells.")
    return main_df


def resolve_path(p: Path, default_dir: Path) -> Path:
    """Resolve bare filenames against default_dir; keep paths with directories as given."""
    p = Path(p)
    if p.parent == Path("."):
        return default_dir / p
    return p


def main():
    parser = argparse.ArgumentParser(
        description="Fill missing Target protein_ID values of a main csv from a reference csv via matching synonyms and Tracer_IDs."
    )
    parser.add_argument(
        "main_input",
        type=Path,
        help="Main CSV. A bare filename is looked up in data/intermediate.",
    )
    parser.add_argument(
        "reference_input",
        type=Path,
        help="Reference CSV with Synonyms and Target protein_ID. A bare filename is looked up in data/intermediate.",
    )
    parser.add_argument(
        "output",
        type=Path,
        nargs="?",
        default=None,
        help="Output CSV. A bare filename is written next to the main file. "
             "Default: <main name>_filled_protein_ids.csv in the same folder as the main file.",
    )
    args = parser.parse_args()

    main_path = resolve_path(args.main_input, DATA_INTERMEDIATE_PATH)
    reference_path = resolve_path(args.reference_input, DATA_INTERMEDIATE_PATH)
    if args.output is None:
        output_path = main_path.with_name(f"{main_path.stem}_filled_protein_ids.csv")
    else:
        output_path = resolve_path(args.output, main_path.parent)

    for path in (main_path, reference_path):
        if not path.is_file():
            parser.error(f"Input file not found: {path}")

    main_df = pd.read_csv(main_path, dtype="string")
    reference_df = pd.read_csv(reference_path, dtype="string")
    for col in ("Synonyms", "Tracer_ID"):
        if col not in main_df.columns:
            parser.error(f'Column "{col}" not found in {main_path}')
    for col in ("Synonyms", "Target protein_ID"):
        if col not in reference_df.columns:
            parser.error(f'Column "{col}" not found in {reference_path}')

    main_df = fill_protein_ids(main_df, reference_df)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    main_df.to_csv(output_path, index=False)
    print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()
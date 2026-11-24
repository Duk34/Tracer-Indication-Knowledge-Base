'''This script can be applied on every csv file that contains a column named "Target gene_ID" holding NCBI Entrez gene IDs.
It maps the gene IDs to UniProtKB IDs (reviewed Swiss-Prot entries) using MyGene.info.
The output is a CSV file with the additional column "Target protein_ID".
If a gene ID has several Swiss-Prot entries, all of them are written, separated by ";".
It also adds a column "Target_species" with the species information.

Use it like this:
python map_target_UniProtKB_ID_and_species.py input.csv [output.csv] [overwrite|fill-missing]

A filename is looked up in data/intermediate. Without an output argument,
<input name>_mapped_uniprot.csv is written next to the input.
Mode "fill-missing" (default) only fills empty cells and keeps existing values,
mode "overwrite" replaces the values in the target column.

eg. python map_target_UniProtKB_ID_and_species.py imageable_genome.csv imageable_genome_mapped_uniprot.csv fill-missing'''


import argparse
from pathlib import Path

import mygene
import pandas as pd

try:
    from .config import *
except ImportError:
    from config import *


#probably we need some more species here
SPECIES_MAP = {
    9606: "Homo sapiens",
    10029: "Cricetulus griseus",
    10090: "Mus musculus",
    10116: "Rattus norvegicus",
}

def assign_column(df: pd.DataFrame, col: str, values: pd.Series, mode: str) -> None:
    """overwrite: replace the column; fill-missing: only fill empty cells."""
    values = values.astype("string")
    if mode == "overwrite" or col not in df.columns:
        df[col] = values
        return
    existing = df[col].astype("string")
    df[col] = existing.where(existing.str.strip().fillna("") != "", values)


def map_gene_ids(curation_df: pd.DataFrame, mode: str = "fill-missing") -> pd.DataFrame:  
    # clean IDs: strip whitespace
    clean = (
        curation_df["Target gene_ID"] 
        .astype("string")
        .str.strip() 
    )
    gene_ids = clean.dropna().unique().tolist() 
    if not gene_ids: 
        print("No gene IDs found, nothing to map.")  
        return curation_df

    print("Mapping gene IDs to UniProtKB IDs...") 
    mg = mygene.MyGeneInfo()
    res = mg.querymany(
        gene_ids,  
        scopes="entrezgene", 
        fields="uniprot.Swiss-Prot, taxid", 
        species="all",
        as_dataframe=True,
    )

    # make sure expected columns exist even if nothing was found
    res = res.reindex(columns=["uniprot.Swiss-Prot", "taxid", "_score", "notfound"])  
    if res["_score"].notna().any():
        res = res.sort_values("_score", ascending=False)
    res = res[~res.index.duplicated(keep="first")]

    # report unmapped IDs
    unmapped = res.index[res["notfound"].fillna(False).astype(bool)]
    if len(unmapped):
        print(f"Warning: {len(unmapped)} IDs not found, e.g. {list(unmapped[:5])}")

    taxid = pd.to_numeric(res["taxid"], errors="coerce").astype("Int64")
    species = taxid.map(SPECIES_MAP).fillna(taxid.astype("string"))  # keep taxid if unknown

    # several Swiss-Prot entries per gene come back as a list, join them with ";"
    uniprot = res["uniprot.Swiss-Prot"].map(lambda v: ";".join(v) if isinstance(v, list) else v) 

    assign_column(curation_df, "Target protein_ID", clean.map(uniprot), mode) 
    assign_column(curation_df, "Target_species", clean.map(species), mode)
    return curation_df


def resolve_path(p: Path, default_dir: Path) -> Path:
    """Bare filename -> default_dir; anything with a directory part is used as given."""
    p = Path(p)
    if p.parent == Path("."):
        return default_dir / p
    return p


def main():
    parser = argparse.ArgumentParser(
        description="Map gene IDs to UniProtKB IDs and species."  
    )
    parser.add_argument(
        "input", type=Path,
        help="Input CSV. A filename is looked up in data/intermediate.",
    )
    parser.add_argument(
        "output", type=Path, nargs="?", default=None,
        help="Output CSV. A filename is written next to the input. "
             "Default: <input name>_mapped_uniprot.csv in the same folder as the input.",  
    )
    parser.add_argument(
        "mode", nargs="?", choices=["overwrite", "fill-missing"], default="fill-missing",
        help="overwrite: replace existing values in the target column. "
             "fill-missing: only fill empty cells and keep existing values (default).",
    )
    args = parser.parse_args()

    input_path = resolve_path(args.input, DATA_INTERMEDIATE_PATH)
    if args.output is None:
        output_path = input_path.with_name(f"{input_path.stem}_mapped_uniprot.csv")  
    else:
        output_path = resolve_path(args.output, input_path.parent)

    if not input_path.is_file():
        parser.error(f"Input file not found: {input_path}")

    curation_df = pd.read_csv(input_path, dtype={"Target gene_ID": "string"})
    if "Target gene_ID" not in curation_df.columns: 
        parser.error(f'Column "Target gene_ID" not found in {input_path}')  

    curation_df = map_gene_ids(curation_df, args.mode) 
    output_path.parent.mkdir(parents=True, exist_ok=True)
    curation_df.to_csv(output_path, index=False)
    print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()
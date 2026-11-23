
import mygene
import pandas as pd

try:
    from .config import *
except ImportError:
    from config import *

INPUT_PATH = DATA_INTERMEDIATE_PATH / "Imagable_Genome" / "Supplementary_Data_2.csv"
OUTPUT_PATH = DATA_INTERMEDIATE_PATH / "imageable_genome.csv"


COLUMNS_ORDER = [
    "Tracer_ID",
    "Tracer_Name",
    "Synonyms",
    "Type",
    "CID",
    "SID",
    "Modality",
    "Radionuclide_ID",
    "Phases",
    "Evidence Level",
    "Target protein_ID",
    "Target protein name",
    "Target gene_ID",
    "Target gene symbol",
    "Disease_ID",
    "Disease name",
    "Target_species",
    "Source (URL)",
    "Mechanism",
    "Year",
    "Curation Notes",
    "Review Status",
]


def clean(value: str) -> str:
    """Remove stray quotes and surrounding whitespace."""
    return value.replace('"', "").strip()


def join_unique(values) -> str:
    """Join values with ';', splitting existing ';' lists and dropping empty/duplicate parts."""
    seen = []
    for value in values:
        for part in str(value).split(";"):
            part = part.strip()
            if part and part not in seen:
                seen.append(part)
    return ";".join(seen)


def ensembl_to_entrez(ensembl_ids: list[str]) -> dict[str, dict]:
    """Map Ensembl gene IDs to Entrez gene ID and symbol via mygene."""
    mg = mygene.MyGeneInfo()
    hits = mg.querymany(
        ensembl_ids,
        scopes="ensembl.gene",
        fields="entrezgene,symbol",
        species="all",
        verbose=False,
    )
    mapping = {}
    for hit in hits:
        if hit.get("notfound") or hit["query"] in mapping:
            continue
        mapping[hit["query"]] = {
            "entrez": str(hit.get("entrezgene", "")),
            "symbol": hit.get("symbol", ""),
        }
    return mapping


def main():
    """Convert the Imageable Genome CSV into the unified curation scheme."""
    # first row is the sheet title, second row the real header
    df = pd.read_csv(INPUT_PATH, header=1, dtype=str, keep_default_na=False)
    df = df.apply(lambda col: col.map(clean))

    # 0 = no name; if the first name is missing, the second name becomes the tracer name
    df[["radiotracer_1", "radiotracer_2"]] = df[["radiotracer_1", "radiotracer_2"]].replace("0", "")
    no_first = df["radiotracer_1"] == ""
    df.loc[no_first, "radiotracer_1"] = df.loc[no_first, "radiotracer_2"]

    # drop rows without any tracer name
    n_no_name = (df["radiotracer_1"] == "").sum()
    df = df[df["radiotracer_1"] != ""]
    

    # some PMIDs are stored as the string "b'28315351'", keep only the digits
    df["pmid"] = df["pmid"].str.extract(r"(\d+)", expand=False).fillna("")

    # one row per Ensembl ID (rows without Ensembl ID keep an empty string)
    df["ensembl"] = df["SIMILAR_ENSEMBL"].str.split(",")
    df = df.explode("ensembl")
    df["ensembl"] = df["ensembl"].str.strip()

    # Ensembl -> Entrez gene ID + symbol (only query non-empty Ensembl IDs)
    valid_ensembl = sorted(e for e in df["ensembl"].unique() if e != "")
    mapping = ensembl_to_entrez(valid_ensembl)

    df["Target gene_ID"] = df["ensembl"].map(lambda e: mapping.get(e, {}).get("entrez", ""))
    df["Target gene symbol"] = df["ensembl"].map(lambda e: mapping.get(e, {}).get("symbol", ""))

    # fields of the curation scheme
    df["Tracer_Name"] = df["radiotracer_1"]
    df["Synonyms"] = [join_unique([a, b]) for a, b in zip(df["radiotracer_1"], df["radiotracer_2"])]
    df["Target protein name"] = [join_unique([a, b]) for a, b in zip(df["protein_1"], df["SIMILAR_PROTEIN"])]
    df["Source (URL)"] = df["pmid"].map(lambda p: f"https://pubmed.ncbi.nlm.nih.gov/{p}/" if p else "")

    # Grouping key: the Ensembl ID, or the protein name if there is no Ensembl ID.
    # This prevents different proteins of the same tracer without a gene from being merged.
    df["group_key"] = df["ensembl"].where(df["ensembl"] != "", "no_ensembl_" + df["protein_1"])

    # one row per tracer-gene pair
    out = (
        df.groupby(["Tracer_Name", "group_key"], sort=False)
        .agg(
            {
                "ensembl": "first",
                "Synonyms": join_unique,
                "Target protein name": join_unique,
                "Target gene_ID": "first",
                "Target gene symbol": "first",
                "Source (URL)": join_unique,
            }
        )
        .reset_index()
    )

    # distinguish between "no Ensembl ID given" and "ID given, but mapping failed"
    no_ensembl = (out["ensembl"] == "").sum()
    not_found = ((out["ensembl"] != "") & (out["Target gene_ID"] == "")).sum()

    out = out.drop(columns=["ensembl", "group_key"])
    out["Curation Notes"] = "Curated from Imageable Genome, Supplementary Data 2 (Nat Commun 2023)"
    out["Review Status"] = "not reviewed"
    out = out.reindex(columns=COLUMNS_ORDER, fill_value="")  # all other columns stay empty

    out.to_csv(OUTPUT_PATH, index=False, encoding="utf-8")
    print(f"{OUTPUT_PATH} ({len(out)} rows)")
    print(f"Dropped rows without any tracer name: {n_no_name}")
    print(f"Rows without Ensembl ID: {no_ensembl}")
    print(f"Ensembl ID present, but Entrez gene ID not found: {not_found}")
    print(f"Total rows without Entrez gene ID: {no_ensembl + not_found}")


if __name__ == "__main__":
    main()
"""Command line interface: `tikb <command> INPUT OUTPUT`.

Each command reads a CSV, runs one step and writes a CSV.
Snakemake calls these commands; you can also run one by hand to test a step.
"""

import argparse

import pandas as pd

from tikb.enrich import targets
from tikb.enrich.pubchem import cid, names, sid, synonyms
from tikb.enrich.radiopharm import data, diseases, ids

COMMANDS = {
    "pubchem-cid": "add PubChem CIDs (needs --matches)",
    "pubchem-sid": "add PubChem SIDs for tracers without CID (needs --matches)",
    "pubchem-synonyms": "add PubChem synonyms for each CID/SID",
    "target-ids": "translate target names into UniProt and Gene IDs (MyGene.info)",
    "radiopharm-ids": "add RadioPharm IDs",
    "radiopharm-data": "fill type, synonyms and targets from RadioPharm",
    "radiopharm-diseases": "one row per tracer and disease from RadioPharm",
}

# IDs are not numbers: pandas must not guess their type.
# Int64 keeps them whole numbers even when some are missing (otherwise 5793 -> 5793.0).
ID_TYPES = {"CID": "Int64", "SID": "Int64"}


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="tikb", description="Tracer-Indication-Knowledge-Base"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name, help_text in COMMANDS.items():
        sub = subparsers.add_parser(name, help=help_text)
        sub.add_argument("input", help="input CSV")
        sub.add_argument("output", help="output CSV")
        sub.add_argument(
            "--matches", help="CSV that shows which name spelling PubChem found"
        )
    args = parser.parse_args()

    df = pd.read_csv(args.input, dtype=ID_TYPES)

    if args.command in ("pubchem-cid", "pubchem-sid"):
        if not args.matches:
            parser.error(f"{args.command} needs --matches")
        if args.command == "pubchem-cid":
            df, matches = cid.add_cids(df)
            id_column = "CID"
        else:
            df, matches = sid.add_sids(df)
            id_column = "SID"
        matches.to_csv(args.matches, index=False)
        print(names.summary(matches, id_column))
    elif args.command == "pubchem-synonyms":
        df = synonyms.add_synonyms(df)
    elif args.command == "target-ids":
        df = targets.add_target_ids(df)
    elif args.command == "radiopharm-ids":
        df = ids.add_radiopharm_ids(df)
    elif args.command == "radiopharm-data":
        df = data.add_radiopharm_data(df)
    elif args.command == "radiopharm-diseases":
        df = diseases.expand_diseases(df)

    # Again before saving, because a step may rebuild the table and lose the types.
    df = df.astype(
        {column: t for column, t in ID_TYPES.items() if column in df.columns}
    )
    df.to_csv(args.output, index=False)
    print(f"Saved {len(df)} rows to {args.output}")


if __name__ == "__main__":
    main()

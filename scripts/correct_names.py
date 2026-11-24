# There happens to be some compounds in the integrated table that are not correctly named, 
# so this script corrects the names of those compounds.

import pandas as pd

try:
    from .config import (
        INTEGRATED_TABLE,
        INTEGRATED_TABLE_CORRECTED,
        CORRECTED_NAMES,
    )
except ImportError:
    from config import (
        INTEGRATED_TABLE,
        INTEGRATED_TABLE_CORRECTED,
        CORRECTED_NAMES,
    )

def main():
    df = pd.read_csv(INTEGRATED_TABLE)
    df["Tracer_ID"] = df["Tracer_ID"].replace(CORRECTED_NAMES)
    df["Tracer_ID"] = df["Tracer_ID"].str.strip()
    df[["CID", "SID"]] = df[["CID", "SID"]].astype("Int64")
    df.to_csv(INTEGRATED_TABLE_CORRECTED, index=False)


if __name__ == "__main__":
    main()
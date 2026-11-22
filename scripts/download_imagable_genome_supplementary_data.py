
"""This scroipt downloads the supplementary data from the Imagable Genome paper and stores it as CSV files in data/intermediate/Imagable_Genome."""

import io
import re

import httpx
import pandas as pd

try:
    from .config import *
except ImportError:
    from config import *

url = "https://static-content.springer.com/esm/art%3A10.1038%2Fs41467-023-43123-3/MediaObjects/41467_2023_43123_MOESM4_ESM.xlsx"


def main():
    """Download the supplementary data from the Imagable Genome paper and store it as CSV files."""
    out_dir = DATA_INTERMEDIATE_PATH/"Imagable_Genome"
    out_dir.mkdir(exist_ok=True)

    response = httpx.get(url, follow_redirects=True, timeout=60)
    response.raise_for_status()

    sheets = pd.read_excel(io.BytesIO(response.content), sheet_name=None, header=None)


    # store every excel sheet as one CSV file in the output directory
    for name, df in sheets.items():
        safe = re.sub(r"[ ]+", "_", name).strip()  # removewhitespace for filenames
        path = out_dir / f"{safe}.csv"
        df.to_csv(path, index=False, header=False)
        print(path)

if __name__ == "__main__":
    main()
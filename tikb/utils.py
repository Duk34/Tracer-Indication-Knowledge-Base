"""Small helpers shared by several modules."""

import pandas as pd


def merge_ids(*values: object) -> str | None:
    """Join semicolon-separated IDs into one string, without duplicates."""
    ids = []
    for value in values:
        if pd.isna(value):
            continue
        for item in str(value).split(";"):
            item = item.strip()
            if item and item not in ids:
                ids.append(item)
    return ";".join(ids) if ids else None

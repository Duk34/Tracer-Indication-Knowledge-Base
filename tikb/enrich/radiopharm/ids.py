"""Step: add the RadioPharm ID (RP...) of each tracer."""

import re

import httpx
import pandas as pd

from tikb.enrich.radiopharm.client import SEARCH_URL, new_client


def fetch_radiopharm_id(
    tracer_name: str, radionuclide: str, client: httpx.Client
) -> str | None:
    """Search RadioPharm for the tracer name and return the first RP... ID in the answer."""
    try:
        response = client.post(
            SEARCH_URL, json={"api": "fullText", "keyword": tracer_name}
        )
        response.raise_for_status()
    except httpx.HTTPError as error:
        print(f"Request failed for {tracer_name}: {error}")
        return None

    # Only accept the ID if the answer also mentions the expected radionuclide.
    text = response.text
    match = re.search(r"\b(RP[A-Z0-9]{6,12})\b", text)
    if match and radionuclide.lower() in text.lower():
        return match.group(1)

    # Fallback: try again without the "[18F]" prefix.
    if tracer_name.startswith(f"[{radionuclide}]"):
        clean_name = tracer_name.replace(f"[{radionuclide}]", "").strip("-")
        return fetch_radiopharm_id(clean_name, radionuclide, client)
    return None


def add_radiopharm_ids(df: pd.DataFrame) -> pd.DataFrame:
    """Add the column Radiopharm_ID."""
    ids = {}
    with new_client() as client:
        for tracer, nuclide in zip(df["Tracer_ID"], df["Radionuclide_ID"]):
            ids[tracer] = fetch_radiopharm_id(tracer, nuclide, client)
            print(f"Radiopharm ID for {tracer}: {ids[tracer]}")
    df["Radiopharm_ID"] = df["Tracer_ID"].map(ids)
    return df

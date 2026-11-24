"""
Fetch radiopharmaceutical data from the radiopharm database.
There is no download possibilities, so the data is fetched directly from the website. 
The data is then used to fill missing entries in the main table.
"""

try:
    from .config import (
        INTEGRATED_TABLE_PROTEIN_ID,
        RADIOPHARM_API_URL,
        INTEGRATED_TABLE_RADIOPHARM
    )
except ImportError:
    from config import (
        INTEGRATED_TABLE_PROTEIN_ID,
        RADIOPHARM_API_URL,
        INTEGRATED_TABLE_RADIOPHARM
    )

import pandas as pd
import httpx
from bs4 import BeautifulSoup
import re







def main():
  df = pd.read_csv(INTEGRATED_TABLE_PROTEIN_ID)
  ids = {}
  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:160.0) Gecko/20100101"
          " Firefox/160.0"
      ),
      "Accept": "application/json, text/plain, */*",
      "Origin": "https://radiopharm.idrblab.cn",
      "Referer": "https://radiopharm.idrblab.cn/search-drug",
  }

  with httpx.Client(
      headers=headers, timeout=15.0, follow_redirects=True
  ) as client:
    for tracer_name, nuclide in zip(df["Tracer_ID"], df["Radionuclide_ID"]):
        ids[tracer_name] = fetch_radiopharm_id(tracer_name, nuclide, client)
        print(f"Fetched Radiopharm ID for {tracer_name}: {ids[tracer_name]}")

    df["Radiopharm_ID"] = df["Tracer_ID"].map(ids)
    df.to_csv(INTEGRATED_TABLE_RADIOPHARM, index=False)


def fetch_radiopharm_id(
    tracer_name: str, radionuclide: str, client: httpx.Client
) -> str | None:
  """Wysyła zapytanie POST do wewnętrznego API RadioPharm i wyciąga ID (RP...)."""
  payload = {"api": "fullText", "keyword": tracer_name}

  try:
    response = client.post(RADIOPHARM_API_URL, json=payload)
    response.raise_for_status()
  except httpx.HTTPError as e:
    print(f"An error occurred while requesting {tracer_name}: {e}")
    return None

  # Szukamy pierwszego identyfikatora RP... bezpośrednio w zwróconym JSON-ie (jako tekst)
  # Zabezpieczenie: sprawdzamy też, czy w odpowiedzi znajduje się oczekiwany radionuklid
  resp_text = response.text
  match = re.search(r"\b(RP[A-Z0-9]{6,12})\b", resp_text)

  if match and radionuclide.lower() in resp_text.lower():
    return match.group(1)

  # Fallback: jeśli nie znaleziono z "[18F]", próbujemy bez prefiksu izotopu
  elif tracer_name.startswith(f"[{radionuclide}]"):
    clean_name = tracer_name.replace(f"[{radionuclide}]", "").strip("-")
    return fetch_radiopharm_id(clean_name, radionuclide, client)

  return None


if __name__ == "__main__":
  main()

"""URLs, headers and JSON requests for the RadioPharm API (shared by all RadioPharm steps)."""

import httpx

API = "https://radiopharm.idrblab.cn/api/radiopharm"
SEARCH_URL = f"{API}/postSearchDrugResult"
DRUG_INFO_URL = f"{API}/getDrugInfo"
DRUG_DESCRIPTION_URL = f"{API}/getDrugDescription"
TARGET_URL = f"{API}/getTarget"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:160.0) Gecko/20100101 Firefox/160.0",
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://radiopharm.idrblab.cn",
    "Referer": "https://radiopharm.idrblab.cn/search-drug",
}


def new_client() -> httpx.Client:
    return httpx.Client(headers=HEADERS, timeout=20.0, follow_redirects=True)


def get_json(client: httpx.Client, url: str) -> dict | None:
    try:
        response = client.get(url)
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, dict) else None
    except (httpx.HTTPError, ValueError) as error:
        print(f"Request failed for {url}: {error}")
        return None

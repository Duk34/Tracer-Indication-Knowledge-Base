"""Get tracer data from the RadioPharm database (https://radiopharm.idrblab.cn).

RadioPharm has no download, only the API its website uses. So every tracer is
looked up one by one: first its RadioPharm ID (ids.py), then its details
(data.py) and diseases (diseases.py). client.py holds the shared API code.
"""

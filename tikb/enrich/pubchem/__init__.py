"""Look up PubChem CIDs, SIDs and synonyms for tracer names.

One file per step (cid, sid, synonyms). client.py and names.py hold the
code that several steps share. Steps never import from each other.
"""

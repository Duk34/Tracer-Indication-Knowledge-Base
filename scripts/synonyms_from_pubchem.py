# Pubchem allows for easy extraction of synonyms for a given compound with its API.

import pandas as pd
import pubchempy
import time

from config import INTEGRATED_TABLE_SID, INTEGRATED_TABLE_SYNONYMS

def main():
    df = pd.read_csv(INTEGRATED_TABLE_SID)
    df_with_cid = df[df["CID"].notna()].copy()
    df_with_sid = df[df["SID"].notna()].copy()

    cid_to_existing_syns = (
    df_with_cid.groupby(df_with_cid["CID"].astype(int))["Synonyms"]
    .apply(parse_synonyms)
    .to_dict()
)

    sid_to_existing_syns = (
    df_with_sid.groupby(df_with_sid["SID"].astype(int))["Synonyms"]
    .apply(parse_synonyms)
    .to_dict()
)
    for cid in df_with_cid["CID"].dropna().unique():
        try:
            compound = pubchempy.Compound.from_cid(int(cid))
            synonyms = set(compound.synonyms)
            existing_syns = cid_to_existing_syns.get(int(cid), set())
            combined_syns = existing_syns.union(synonyms)
            cid_to_existing_syns[int(cid)].update(combined_syns)
        except Exception as e:
            print(f"Error fetching synonyms for CID {cid}: {e}")
            time.sleep(1)  # Wait for a second before retrying
            try:
                compound = pubchempy.Compound.from_cid(int(cid))
                synonyms = set(compound.synonyms)
                existing_syns = cid_to_existing_syns.get(int(cid), set())
                combined_syns = existing_syns.union(synonyms)
                cid_to_existing_syns[int(cid)].update(combined_syns)
            except Exception as e:
                print(f"Retry failed for CID {cid}: {e}")
        time.sleep(0.25)  # To avoid hitting the API rate limit

    for sid in df_with_sid["SID"].dropna().unique():
        try:
            substance = pubchempy.Substance.from_sid(int(sid))
            synonyms = set(substance.synonyms)
            existing_syns = sid_to_existing_syns.get(int(sid), set())
            combined_syns = existing_syns.union(synonyms)
            sid_to_existing_syns[int(sid)].update(combined_syns)
        except Exception as e:
            print(f"Error fetching synonyms for SID {sid}: {e}")
            time.sleep(1)  # Wait for a second before retrying
            try:
                substance = pubchempy.Substance.from_sid(int(sid))
                synonyms = set(substance.synonyms)
                existing_syns = sid_to_existing_syns.get(int(sid), set())
                combined_syns = existing_syns.union(synonyms)
                sid_to_existing_syns[int(sid)].update(combined_syns)
            except Exception as e:
                print(f"Retry failed for SID {sid}: {e}")
        time.sleep(0.25)  # To avoid hitting the API rate limit
    
    
    cid_str_map = {
    int(cid): ";".join(sorted(s.strip() for s in syns if str(s).strip()))
    for cid, syns in cid_to_existing_syns.items()
    if syns
}

    sid_str_map = {
        int(sid): ";".join(sorted(s.strip() for s in syns if str(s).strip()))
        for sid, syns in sid_to_existing_syns.items()
        if syns
    }

    # Aktualizacja wierszy posiadających CID
    mask_cid = df["CID"].notna()
    df.loc[mask_cid, "Synonyms"] = (
        df.loc[mask_cid, "CID"]
        .astype(int)
        .map(cid_str_map)
        .fillna(df.loc[mask_cid, "Synonyms"])
    )

    # Aktualizacja wierszy posiadających SID
    mask_sid = df["SID"].notna()
    df.loc[mask_sid, "Synonyms"] = (
        df.loc[mask_sid, "SID"]
        .astype(int)
        .map(sid_str_map)
        .fillna(df.loc[mask_sid, "Synonyms"])
    )
    df["CID"] = df["CID"].astype("Int64")
    df["SID"] = df["SID"].astype("Int64")
    df.to_csv(INTEGRATED_TABLE_SYNONYMS, index=False)
    
def parse_synonyms(series):
  result = set()
  for val in series.dropna():
    result.update(s.strip() for s in str(val).split(";") if s.strip())
  return result



        

if __name__ == "__main__":
    main()
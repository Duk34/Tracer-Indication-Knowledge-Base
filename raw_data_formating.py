# I downloaded the raw data from the following links:
# https://www.fda.gov/media/76860/download?attachment - orange book (FDA)
# https://www.ema.europa.eu/en/documents/report/medicines-output-medicines-report_en.xlsx - medicines output report (EMA)
# https://www.ncbi.nlm.nih.gov/books/NBK5330/bin/micad.csv - micad (NCBI) this is only a summary of the micad database, which is a database of antimicrobial drugs. The full database is not available for download, but can be accessed through the NCBI website.
# unfortunately the downloand links on the website https://radiopharm.idrblab.cn/download are not working, if they are fixed this will also need to be integrated.
import pandas as pd
from pathlib import Path
import csv

DATA_RAW_PATH = Path("data/raw/")
DATA_INTERMEDIATE_PATH = Path("data/intermediate/")


# TODO: Automatic download of raw data?
# The orange book from the FDA gets updated every month so implementing this could
# future-proof the script a bit.

def main():
    fda_to_csv()
    ema_to_csv()
    micad_to_csv()   

def fda_to_csv():
    # Read the FDA orange book data
    fda_data = pd.read_csv(DATA_RAW_PATH/"products.txt", sep='~', on_bad_lines='warn')
    # Convert to CSV
    fda_data.to_csv(DATA_INTERMEDIATE_PATH/"fda_orange_book.csv", index=False)
    return fda_data

def ema_to_csv():
    # Read the EMA medicines output report data
    ema_data = pd.read_excel(DATA_RAW_PATH/"medicines-output-medicines-report_en.xlsx", header=8)
    # Convert to CSV
    ema_data.to_csv(DATA_INTERMEDIATE_PATH/"ema_medicines_output_report.csv", index=False)
    return ema_data


# Although the micad database already comes in .csv format there is a formatting error at line 809.
# (PMID = 20641621), there appears to be a column shift in this row
# Since this might be fixed in the future, or on the other hand similar mistakes can occur,
# all the rows with uncorrect ammount of columns will be saved to a separate .CSV file for manual examination
def micad_to_csv():
    bad_lines = []
    def collect_bad_lines(bad_line):
        bad_lines.append(bad_line)
        print(f"Warning! Following line was Skipped due to invalid format\n{bad_line[:3]}...")
        return 
    micad_data = pd.read_csv(DATA_RAW_PATH/"micad.csv", on_bad_lines=collect_bad_lines, engine='python')


    # AI generated part, pandas does not allow exporting to csv when the number of columns does not match the columns names
    # using csv package instead.
    if bad_lines:
      out_path = DATA_INTERMEDIATE_PATH / "micad_bad_lines.csv"
      with open(out_path, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        # To get a better view on the bad structure save it to separate csv file 
        writer.writerow(list(micad_data.columns))
        writer.writerows(bad_lines)
    micad_data["PMID"] = micad_data["PMID"].astype("Int64")
    micad_data.to_csv(DATA_INTERMEDIATE_PATH/"micad.csv", index=False)
    return micad_data

def radiopharm_to_csv():
    pass


if __name__ == "__main__":
    main()
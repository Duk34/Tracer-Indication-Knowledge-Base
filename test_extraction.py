# I don't have any experience with text-mining and other NLP techniques, to familiarize myself with it I try to extract some valuable information about
# the FDA approved tracers for PET imaging. That can be found here: https://www.radiopharmaceuticals.info/pet-radiopharmaceuticals.html 
# The information I'll try to extract is the name of the tracer, the target, and the indication.

import httpx # this library is used to make HTTP requests - like downloading a webpage's HTML content
from bs4 import BeautifulSoup # this library is used to parse HTML content and extract information from it
import pandas as pd
from urllib.parse import urljoin # this library is used to join the base URL with the relative URLs of the links extracted from the webpage
import en_ner_bc5cdr_md

URL = "https://www.radiopharmaceuticals.info/pet-radiopharmaceuticals.html"

def main():
    # Downloading the webpage's HTML content
    soup = download_and_parse_html(URL)

    hrefs = soup.select('div.paragraph a')  # Extracting all links from the specified div

    links = []  # Initializing an empty list to store the extracted links
    for href in hrefs:
        links.append(href.get('href'))  # Getting the href attribute of each link

    # For this specific case, two last extracted links are not relevant, so we remove them from the list
    links = links[:-2]


    # Loop that downloads the HTML content of each link and extracts the name, and description of the tracer, and stores them in a list of dictionaries.
    tracer_info_list = []
    for link_suffix in links:
        link = urljoin(URL, link_suffix)  # Joining the base URL with the relative URL of the link
        soup = download_and_parse_html(link)  # Downloading and parsing the HTML content of the link

        name = " ".join(strong.get_text(separator=" ", strip=True) for strong in soup.select('h2 strong')) # Extracting the name of the tracer from the specified h2 tag
        description = " ".join(span.get_text(strip=True) for span in soup.select('div.paragraph'))  # Extracting the description of the tracer from the specified div

        # Removing any unwanted characters from the extracted name and description, everything that follows the first occurence of Dose, including the word Dose itself, is removed from the description.
        description = description.split("Dose")[0].strip().replace("\xa0", " ").replace("\u200b", " ")  # Removing everything that follows the first occurrence of "Dose" in the description
        
        # Appending the extracted information to the list of dictionaries.
        tracer_info_list.append({
            "name": name,
            "raw_description": description,
            "source": link  # Adding the source link to the extracted information
        })


    # Loading the pre-trained biomedical NER model and extracting the target disease from the raw description of each tracer.
    # IMPORTANT: This works only with python 3.12 
    nlp = en_ner_bc5cdr_md.load()
    for tracer_info in tracer_info_list:
        doc = nlp(tracer_info["raw_description"])
        diseases = sorted({
            entity.text for entity in doc.ents if entity.label_ == "DISEASE"
        })

        tracer_info["target_disease"] = {i: get_disease_id(i) for i in diseases}  # Storing the extracted target diseases and their corresponding disease IDs in the tracer_info dictionary.


    # Assinging the evidence level based on the source.
    for tracer_info in tracer_info_list:
        tracer_info["evidence_level"] = 4 if "target_disease" in tracer_info and tracer_info["target_disease"] else None

    # Creating a pandas DataFrame from the list of dictionaries and saving it as a CSV file.
    df = pd.DataFrame(tracer_info_list)

    new_order = ["name", "target_disease", "evidence_level", "raw_description", "source"]  # Defining the new order of the columns
    df = df[new_order]
    df.to_csv("tracer_info.csv", index=False)  # Saving the DataFrame


# This functions downloads the HTML content of a given URL and parses it using BeautifulSoup.
def download_and_parse_html(url):
    response = httpx.get(url)
    html_content = response.text
    soup = BeautifulSoup(html_content, "html.parser")
    return soup


def get_disease_id(disease_name):
    # This function takes a disease name as input and returns the corresponding disease ID from the Disease Ontology database.
    # It constructs a URL to query the Disease Ontology API for the given disease name, sends a GET request to that URL, and parses the JSON response to extract the disease ID.
    # If the disease name is not found in the database, it returns None.
    # The documentation can be found here: https://www.ebi.ac.uk/ols4/api-docs in the api/search section.
    URL = "https://www.ebi.ac.uk/ols4/api/search"

    # As specified in the documentation, the parameters for the GET request are:
    # q: the disease name to search for
    # ontology: the ontology to search in, in this case "mesh"
    # type: the type of entity to search for, in this case "class" means ~ disease
    # rows: the number of results to return, in this case 1 means we only want the first result
    params = {
        "q": disease_name,
        "ontology": ["mesh"],
        "type": "class",
        "rows": 1
    }
    response = httpx.get(URL, params=params)
    data = response.json()

    # Autocomplete completed this but it works
    if data['response']['numFound'] > 0:
        return data['response']['docs'][0]['obo_id']
    else:
        return None

if __name__ == "__main__":
    main()
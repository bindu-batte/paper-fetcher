import requests
import pandas as pd
import argparse
import xml.etree.ElementTree as ET

# Function to fetch paper IDs from PubMed
def fetch_pubmed_ids(query):
    params = {
        "db": "pubmed",
        "term": query,
        "retmode": "json",
        "retmax": 10  # Fetch top 10 results
    }
    response = requests.get(PUBMED_SEARCH_URL, params=params)
    if response.status_code != 200:
        print("Error fetching data from PubMed")
        return []
    
    data = response.json()
    return data.get("esearchresult", {}).get("idlist", [])

# Function to fetch paper details
def fetch_pubmed_details(pubmed_id):
    params = {
        "db": "pubmed",
        "id": pubmed_id,
        "retmode": "xml"
    }
    response = requests.get(PUBMED_FETCH_URL, params=params)
    if response.status_code != 200:
        return None

    return response.text

# Function to parse PubMed XML response
def parse_pubmed_xml(xml_data):
    root = ET.fromstring(xml_data)
    article = root.find(".//PubmedArticle")
    
    if article is None:
        return None

    # Extract key information
    pubmed_id = article.findtext(".//PMID")
    title = article.findtext(".//ArticleTitle")
    publication_date = article.findtext(".//PubDate/Year") or "N/A"
    
    authors = []
    non_academic_authors = []
    company_affiliations = []
    corresponding_email = "N/A"

    # Parse author information
    for author in article.findall(".//Author"):
        last_name = author.findtext("LastName", default="Unknown")
        first_name = author.findtext("ForeName", default="")
        full_name = f"{first_name} {last_name}".strip()

        affiliation = author.findtext(".//Affiliation", default="Unknown")
        email = author.findtext(".//ElectronicAddress")

        authors.append(full_name)

        # Check for non-academic affiliation
        if any(keyword in affiliation.lower() for keyword in ["pharma", "biotech", "company", "inc", "corp"]):
            non_academic_authors.append(full_name)
            company_affiliations.append(affiliation)

        # Capture corresponding author email
        if email:
            corresponding_email = email

    return {
        "PubmedID": pubmed_id,
        "Title": title,
        "Publication Date": publication_date,
        "Non-academic Author(s)": ", ".join(non_academic_authors),
        "Company Affiliation(s)": ", ".join(set(company_affiliations)),
        "Corresponding Author Email": corresponding_email
    }

# Command-line interface
def main():
    parser = argparse.ArgumentParser(description="Fetch PubMed papers based on a search query.")
    parser.add_argument("query", help="Search query for PubMed")
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("-f", "--file", type=str, help="Save results to CSV file")

    args = parser.parse_args(args=[])

    if args.debug:
        print(f"Searching PubMed for: {args.query}")

    pubmed_ids = fetch_pubmed_ids(args.query)
    if not pubmed_ids:
        print("No papers found.")
        return

    results = []
    for pubmed_id in pubmed_ids:
        xml_data = fetch_pubmed_details(pubmed_id)
        if xml_data:
            paper_info = parse_pubmed_xml(xml_data)
            if paper_info:
                results.append(paper_info)

    if not results:
        print("No relevant papers found.")
        return

    df = pd.DataFrame(results)

    if args.file:
        df.to_csv(args.file, index=False)
        print(f"Results saved to {args.file}")
    else:
        print(df)

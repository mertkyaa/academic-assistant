import requests
import time

OPENALEX_URL= "https://api.openalex.org/works"
MAX_ENTRIES = 3
CONTACT_EMAIL= "mertkaya1@ogr.bandirma.edu.tr"

SELECT_FIELDS= "id,title,abstract_inverted_index,authorships,cited_by_count,publication_date,doi"

def fetch_with_retry(params):
    for attempt in range(MAX_ENTRIES):
        response = requests.get(OPENALEX_URL, params=params, timeout=10)

        if response.status_code == 200:
            return response.json()
        

        if response.statuc_code == 429:
            wait_Seconds = 2 ** attempt
            time.sleep(wait_Seconds)
            continue


        print(f"Unexpected HTTP error: {response.status_code}")

    print("All entries failed.")
    return None


def reconstruct_abstract(inverted_index):
    if not inverted_index:
        return None
    
    position_word_pairs = []

    for word, positions in inverted_index.items():
        for position in positions:
            position_word_pairs.append((position, word))

    position_word_pairs.sort()
    return " ".join(word for position, word in position_word_pairs)    


def search_openalex(query, max_results=5):
    params = {
        "search": query,
        "per-page": max_results,
        "select": SELECT_FIELDS,
        "mailto": CONTACT_EMAIL,
    }


    data = fetch_with_retry(params)

    if data is None:
        return []

    papers = []

    for item in data.get("results", []):
        authorships = item.get("authorships", [])
        authors = [entry.get("author", {}).get("display_name") for entry in authorships]

        paper = {
            "source": "openalex",
            "paper_id": item.get("id"),
            "title": item.get("title"),
            "abstract": reconstruct_abstract(item.get("abstract_inverted_index")),
            "url": item.get("doi") or item.get("id"),
            "published": item.get("publication_date"),
            "authors": authors,
            "citation_count": item.get("cited_by_count"),
        }
        papers.append(paper)

    return papers


# --- Adım 6: test bloğu ---
if __name__ == "__main__":
    results = search_openalex("multi-agent systems", max_results=3)

    for paper in results:
        print(paper["title"])
        print("Atıf:", paper["citation_count"], "| Tarih:", paper["published"])
        print(paper["authors"])
        print((paper["abstract"] or "")[:200])
        print("-" * 60)    
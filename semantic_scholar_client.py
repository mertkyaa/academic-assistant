import time
import requests

from config import SEMANTIC_SCHOLAR_KEY

SEMANTIC_SCHOLAR_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
MAX_RETRIES = 3
REQUEST_DELAY = 1.1

FIELDS = "paperId,title,abstract,authors,citationCount,publicationDate,url"

HEADERS = {"x-api-key": SEMANTIC_SCHOLAR_KEY}


def fetch_with_retry(params):
    for attempt in range(MAX_RETRIES):
        time.sleep(REQUEST_DELAY)

        response = requests.get(
            SEMANTIC_SCHOLAR_URL,
            params=params,
            headers=HEADERS,
            timeout=10,
        )

        if response.status_code == 200:
            return response.json()

        if response.status_code == 429:
            wait_seconds = 2 ** attempt
            print(f"Rate limit. {wait_seconds} saniye bekleniyor... (deneme {attempt + 1}/{MAX_RETRIES})")
            time.sleep(wait_seconds)
            continue

        if response.status_code == 403:
            print("403: API key geçersiz veya eksik.")
            return None

        print(f"Beklenmeyen HTTP durumu: {response.status_code}")
        return None

    print("Tüm denemeler başarısız oldu.")
    return None


def search_semantic_scholar(query, max_results=5):
    params = {
        "query": query,
        "limit": max_results,
        "fields": FIELDS,
    }

    data = fetch_with_retry(params)

    if data is None:
        return []

    papers = []

    for item in data.get("data", []):
        paper = {
            "source": "semantic_scholar",
            "paper_id": item.get("paperId"),
            "title": item.get("title"),
            "abstract": item.get("abstract"),
            "url": item.get("url"),
            "published": item.get("publicationDate"),
            "authors": [author.get("name") for author in item.get("authors", [])],
            "citation_count": item.get("citationCount"),
        }
        papers.append(paper)

    return papers


if __name__ == "__main__":
    results = search_semantic_scholar("retrieval augmented generation", max_results=3)

    for paper in results:
        print(paper["title"])
        print("Atıf:", paper["citation_count"], "| Tarih:", paper["published"])
        print(paper["authors"])
        print("-" * 60)
import feedparser
import urllib.parse

# Milestone 3 Section 1

ARXIV_API_URL = "http://export.arxiv.org/api/query"


def search_arxiv(query, max_results=5):
    encoded_query = urllib.parse.quote(query)
    url = f"{ARXIV_API_URL}?search_query=all:{encoded_query}&max_results={max_results}&sortBy=relevance"
    feed = feedparser.parse(url)
    
    papers = []

    for entry in feed.entries:
        paper = {
            "source": "arxiv",
            "paper_id": entry.id,
            "title": entry.title.replace("\n", " ").strip(),
            "abstract": entry.summary.replace("\n", " ").strip(),
            "url": entry.link,
            "published": entry.published,
            "authors": [author.name for author in entry.authors],
            "citation_count": None,
        }
        papers.append(paper)

    return papers

if __name__ == "__main__":
    results = search_arxiv("multi-agent systems", max_results=3)

    for paper in results:
        print(paper["title"])
        print(paper["authors"])
        print(paper["url"])
        print("-" * 60)
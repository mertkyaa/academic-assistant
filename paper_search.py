from arxiv_client import search_arxiv
from openalex_client import search_openalex
from semantic_scholar_client import search_semantic_scholar


# --- header normalization ---
def normalize_title(title):
    if not title:
        return ""

    cleaned = title.lower()

    for char in [".", ",", ":", ";", "-", "–", "?", "!", "(", ")"]:
        cleaned = cleaned.replace(char, " ")

    return " ".join(cleaned.split())


# --- deduplicate ---
def deduplicate(papers):
    seen_titles = set()
    unique_papers = []

    for paper in papers:
        key = normalize_title(paper.get("title"))

        if key in seen_titles:
            continue

        seen_titles.add(key)
        unique_papers.append(paper)

    return unique_papers


# --- main: get three source, merge and sort ---
def search_papers(query, max_results=5):
    all_papers = []

    sources = [
        ("semantic_scholar", search_semantic_scholar),
        ("openalex", search_openalex),
        ("arxiv", search_arxiv),
    ]

    for source_name, search_function in sources:
        try:
            results = search_function(query, max_results=max_results)
            print(f"{source_name}: {len(results)} papers found")
            all_papers.extend(results)
        except Exception as error:
            print(f"{source_name} failed: {error}")

    unique_papers = deduplicate(all_papers)

    unique_papers.sort(key=lambda paper: paper.get("citation_count") or 0, reverse=True)

    return unique_papers


# --- test ---
if __name__ == "__main__":
    papers = search_papers("retrieval augmented generation", max_results=5)

    print(f"\nAll {len(papers)} single paper\n")

    for index, paper in enumerate(papers, start=1):
        print(f"{index}. {paper['title']}")
        print(f"   Sources: {paper['source']} | Atıf: {paper['citation_count']}")
        print()
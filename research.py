import sys
from config import validate_config
from paper_search import search_papers
from filter_agent import run_filter_agent
from summary_agent import run_summary_agent

def main():
    if len(sys.argv) < 2:
        print('Usage: python research.py "your research topic"')
        sys.exit(1)

    topic = sys.argv[1]
    validate_config()

    # 1. Search
    print(f"\n[1/3] Searching papers for: {topic}")
    papers = search_papers(topic, max_results=5)
    print(f"      Found {len(papers)} papers")

    if not papers:
        print("No papers found. Exiting.")
        sys.exit(1)

    # 2. Filter
    print(f"\n[2/3] Filtering and scoring...")
    scored = run_filter_agent(papers, topic)
    print(f"      Scored {len(scored)} papers")

    if not scored:
        print("Filter agent returned no results. Exiting.")
        sys.exit(1)

    # 3. Summarize
    print(f"\n[3/3] Generating summary...")
    summary = run_summary_agent(scored, topic)

    print(f"\n{'='*60}")
    print(summary)
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
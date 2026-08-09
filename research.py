import sys
from config import validate_config
from search_agent import run_agent


def main():
    if len(sys.argv)<2:
        print('Usage: python research.py "your research topic"')
        sys.exit(1)


    topic = sys.argv[1]

    validate_config()

    question = (
        f"Find and summarize the most important academic papers about: {topic}."
        "For each paper, explain in simple language what problem it solves "
        "and what it matters. Write for a student audience."

    )
    run_agent(question)

if __name__ == "__main__":
    main()        
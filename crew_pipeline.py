from crewai import Agent, Task , Crew, Process, LLM
from crewai.tools import tool
from paper_search import search_papers
from search_agent import format_papers_for_agent
import sys




llm = LLM(
    model = "anthropic/claude-haiku-4-5-20251001",
    max_tokens=4096
)

@tool("search_academic_papers")
def search_papers_tool(query: str) -> str:
    """Search academic papers from arXiv, OpenAlex, and Semantic Scholar.
    Use this to find research papers on any scientific topic.
    Returns a formatted list of papers with titles, abstracts, citations, and URLs.
    
    """

    results = search_papers(query,max_results=5)

    if not results:
        return "No papers found for this query."
    

    return format_papers_for_agent(results)


search_agent = Agent(
    role="Academic Paper Researcher",
    goal="Find the most relevant academic papers on the given research topic",
    backstory="You are a research assistant who searches academic databases to find relevant papers. You always use your search tool to find papers - never make up results.",
    tools=[search_papers_tool],
    llm=llm,
    verbose=True
)

filter_agent = Agent(
    role="Paper Relevance Analyst",
    goal="Score and rank papers by relevance, recency, and citation impact",
    backstory="You are an expert at evaluating academic papers. You score each paper on three criteria (relevance 0-10, recency 0-10, impact 0-10) and provide a total score with a brief justification.",
    llm=llm,
    verbose=True
)

summary_agent = Agent(
    role="Student-Friendly Paper Summarizer",
    goal="Write clear, accessible summaries of academic papers for university students",
    backstory="You summarize academic research in simple language that undergraduate students can understand. You avoid jargon and explain complex concepts with everyday analogies.",
    llm=llm,
    verbose=True
)

def build_tasks(topic: str):
    """Create the three pipeline tasks for a given research topic."""
    
    search_task = Task(
        description=f"Search for academic papers about: {topic}. Use your search tool to find relevant papers. Return all the paper details you find.",
        expected_output="A list of academic papers with titles, abstracts, authors, citation counts, and URLs.",
        agent=search_agent
    )

    filter_task = Task(
        description=f"Analyze and score the following papers for the research topic: {topic}. Score each paper on three criteria: relevance (0-10), recency (0-10), and impact (0-10). Calculate a total score. Return ONLY valid JSON array.",
        expected_output='A JSON array where each element has: paper_id, title, relevance, recency, impact, total, reason.',
        agent=filter_agent
    )

    summary_task = Task(
        description=f"Write a student-friendly summary of the top-scored papers about: {topic}. Use simple language, avoid jargon, and explain why these papers matter. Write 2-3 paragraphs.",
        expected_output="A 2-3 paragraph summary in plain language suitable for undergraduate students.",
        agent=summary_agent
    )

    return [search_task, filter_task, summary_task]

def run_crew(topic: str):
    """Run the full research pipeline using CrewAI."""
    tasks = build_tasks(topic)
    
    crew = Crew(
        agents=[search_agent, filter_agent, summary_agent],
        tasks=tasks,
        process=Process.sequential,
        verbose=True
    )
    
    results = crew.kickoff()
    return results


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python crew_pipeline.py \"search topic\"")
        sys.exit(1)
    
    topic = sys.argv[1]
    print(f"Starting CrewAI pipeline for: {topic}")
    print("=" * 60)
    
    results = run_crew(topic)
    
    print("=" * 60)
    print("FINAL RESULT:")
    print("=" * 60)
    print(results)        
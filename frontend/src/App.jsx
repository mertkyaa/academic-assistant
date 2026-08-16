import { useState } from "react"

function App() {
  const [topic, setTopic] = useState("")
  const [synthesis, setSynthesis] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  async function handleSearch() {
    if (!topic.trim()) return

    setLoading(true)
    setSynthesis(null)
    setError("")

    try {
      const response = await fetch("http://localhost:8000/api/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic: topic })
      })

      if (!response.ok) {
        throw new Error("Server error: " + response.status)
      }

      const data = await response.json()
      setSynthesis(data.synthesis)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  function PaperCard({ paperId, papers }) {
    const paper = papers[paperId]
    if (!paper) return null

    const year = paper.published ? paper.published.slice(0, 4) : ""
    const authors = paper.authors ? paper.authors.slice(0, 2).join(", ") : ""
    const source = paper.source || ""

    const sourceColors = {
      arxiv: "bg-red-100 text-red-700",
      semantic_scholar: "bg-purple-100 text-purple-700",
      openalex: "bg-green-100 text-green-700"
    }
    const isHighImpact = paper.citation_count && paper.citation_count > 1000

    return (
      <a href={paper.url} target="_blank" rel="noopener noreferrer"
         className={`block border rounded-lg p-3 transition-all
           ${isHighImpact
             ? "border-yellow-300 bg-yellow-50 hover:border-yellow-400 hover:shadow-md"
             : "border-gray-200 hover:border-blue-400 hover:shadow-md"
           }`}>
        <p className="text-blue-700 font-medium text-sm leading-snug">
          {paper.title}
        </p>
        <div className="flex flex-wrap items-center gap-2 mt-2 text-xs text-gray-500">
          {authors && <span>{authors}</span>}
          {year && <span>· {year}</span>}
          {paper.citation_count != null && (
            <span className="bg-yellow-100 text-yellow-700 px-2 py-0.5 rounded-full font-medium">
              {paper.citation_count} citations
            </span>
          )}
          {source && (
            <span className={`px-2 py-0.5 rounded-full font-medium ${sourceColors[source] || "bg-gray-100 text-gray-600"}`}>
              {source}
            </span>
          )}
          {paper.paper_type && paper.paper_type !== "research" && (
            <span className="bg-indigo-100 text-indigo-700 px-2 py-0.5 rounded-full font-medium">
              {paper.paper_type}
            </span>
          )}
        </div>
      </a>
    )
  }

  function SourceList({ paperIds, papers, label }) {
    if (!paperIds || paperIds.length === 0) return null

    return (
      <div className="mt-3 pt-3 border-t border-gray-100">
        <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">
          {label || "Sources"}
        </p>
        <div className="space-y-2">
          {paperIds.map((id) => (
            <PaperCard key={id} paperId={id} papers={papers} />
          ))}
        </div>
      </div>
    )
  }

  const paperCount = synthesis && synthesis.papers
    ? Object.keys(synthesis.papers).length
    : 0

  return (
    <div className="min-h-screen bg-gray-100">
      <div className="bg-gradient-to-r from-blue-700 to-indigo-800 text-white py-10 px-4 text-center">
        <h1 className="text-4xl font-bold tracking-tight font-heading">
          Academic Paper Assistant
        </h1>
        <p className="mt-2 text-blue-200 text-lg">
          Search, filter, and summarize research papers with AI
        </p>
      </div>

      <div className="max-w-3xl mx-auto mt-10 px-4">
        <div className="flex gap-2">
          <input
            type="text"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            placeholder="Enter a research topic..."
            className="flex-1 border border-gray-300 rounded-lg px-4 py-3 text-lg
                       focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-sm"
          />
          <button
            onClick={handleSearch}
            disabled={loading}
            className="bg-blue-600 text-white px-6 py-3 rounded-lg text-lg
                       font-medium hover:bg-blue-700
                       disabled:bg-blue-400 disabled:cursor-not-allowed shadow-sm"
          >
            {loading ? "Searching..." : "Search"}
          </button>
        </div>

        {loading && (
          <div className="mt-8 flex flex-col items-center gap-3">
            <div className="w-8 h-8 border-4 border-blue-200 border-t-blue-600
                            rounded-full animate-spin" />
            <p className="text-gray-500">
              Scanning arXiv, Semantic Scholar & OpenAlex...
            </p>
          </div>
        )}

        {error && (
          <div className="mt-6 bg-red-50 border border-red-200 rounded-lg p-4
                          text-red-700 text-center">
            {error}
          </div>
        )}

        {!loading && synthesis && (
          <div className="mt-8 space-y-6">

            <div className="bg-white border border-gray-200 rounded-xl shadow-sm p-5
            border-t-4 border-t-indigo-500">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-2xl font-bold text-gray-800 font-heading">
                  {synthesis.title}
                </h2>
                <span className="text-sm bg-blue-100 text-blue-700 px-3 py-1
                                 rounded-full font-medium whitespace-nowrap">
                  {paperCount} papers
                </span>
              </div>
              <p className="text-gray-700 leading-7 text-justify font-academic">
                {synthesis.overview}
              </p>
            </div>

            {synthesis.themes && synthesis.themes.map((theme, i) => (
              <div key={i} className="bg-white border-l-4 border-l-blue-500
                                      border border-gray-200 rounded-xl shadow-sm p-5">
                <h3 className="text-lg font-semibold text-gray-800 mb-2 font-heading">
                  <span className="text-blue-500 mr-2">{i + 1}.</span>
                  {theme.title}
                </h3>
                <p className="text-gray-700 leading-7 text-justify font-academic">
                  {theme.summary}
                </p>
                <SourceList paperIds={theme.paper_ids} papers={synthesis.papers} />
              </div>
            ))}

            {synthesis.trends && synthesis.trends.length > 0 && (
              <div className="bg-white border-l-4 border-l-emerald-500
                              border border-gray-200 rounded-xl shadow-sm p-5">
                <h3 className="text-lg font-semibold text-gray-800 mb-2 font-heading">
                  Research Trends
                </h3>
                {synthesis.trends.map((t, i) => (
                  <div key={i} className="mb-4 last:mb-0">
                    <p className="text-gray-700 leading-7 text-justify font-academic">{t.trend}</p>
                    <SourceList paperIds={t.paper_ids} papers={synthesis.papers}
                                label="Related papers" />
                  </div>
                ))}
              </div>
            )}

            {synthesis.open_problems && synthesis.open_problems.length > 0 && (
              <div className="bg-white border-l-4 border-l-amber-500
                              border border-gray-200 rounded-xl shadow-sm p-5">
                <h3 className="text-lg font-semibold text-gray-800 mb-2 font-heading">
                  Open Problems
                </h3>
                {synthesis.open_problems.map((p, i) => (
                  <div key={i} className="mb-4 last:mb-0">
                    <p className="text-gray-700 leading-7 text-justify font-academic">{p.problem}</p>
                    <SourceList paperIds={p.paper_ids} papers={synthesis.papers}
                                label="Relevant papers" />
                  </div>
                ))}
              </div>
            )}

            {synthesis.where_to_start && synthesis.where_to_start.length > 0 && (
              <div className="bg-blue-50 border-l-4 border-l-indigo-500
                              border border-blue-200 rounded-xl shadow-sm p-5">
                <h3 className="text-lg font-semibold text-gray-800 mb-2 font-heading">
                  Where to Start
                </h3>
                <div className="space-y-3">
                  {synthesis.where_to_start.map((w, i) => (
                    <div key={i}>
                      <PaperCard paperId={w.paper_id} papers={synthesis.papers} />
                      <p className="text-sm text-gray-600 mt-1 ml-3">
                        {w.reason}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}

          </div>
        )}
      </div>

      <footer className="text-center text-gray-400 text-sm mt-12 pb-6">
        Academic Research AI Tool
      </footer>
    </div>
  )
}

export default App
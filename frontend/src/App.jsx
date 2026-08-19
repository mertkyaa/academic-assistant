import { useState, useEffect } from "react"

const TOPICS = [
  "machine learning",
  "deep learning",
  "transformer architecture",
  "large language models",
  "natural language processing",
  "computer vision",
  "object detection",
  "reinforcement learning",
  "retrieval augmented generation",
  "generative adversarial networks",
  "neural networks",
  "support vector machines",
  "transfer learning",
  "federated learning",
  "graph neural networks",
  "attention mechanism",
  "image classification",
  "text classification",
  "sentiment analysis",
  "speech recognition",
]

const RECENT_KEY = "academic-assistant-recent"
const TOKEN_KEY = "academic-assistant-token"
const EMAIL_KEY = "academic-assistant-email"
const MAX_RECENT = 5

function App() {
  const [topic, setTopic] = useState("")
  const [synthesis, setSynthesis] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [selectedIndex, setSelectedIndex] = useState(-1)
  const [recentSearches, setRecentSearches] = useState([])

  // Auth state
  const [token, setToken] = useState(null)
  const [userEmail, setUserEmail] = useState("")
  const [authEmail, setAuthEmail] = useState("")
  const [authPassword, setAuthPassword] = useState("")
  const [authMode, setAuthMode] = useState("login")
  const [authLoading, setAuthLoading] = useState(false)
  const [authError, setAuthError] = useState("")
  const [showAuthModal, setShowAuthModal] = useState(false)

  // Load token and recent searches on mount
  useEffect(() => {
    try {
      const savedToken = localStorage.getItem(TOKEN_KEY)
      const savedEmail = localStorage.getItem(EMAIL_KEY)
      if (savedToken) {
        setToken(savedToken)
        setUserEmail(savedEmail || "")
      }
    } catch {}

    try {
      const saved = localStorage.getItem(RECENT_KEY)
      if (saved) setRecentSearches(JSON.parse(saved))
    } catch {}
  }, [])

  // Show auth modal after 3 seconds if not logged in
  useEffect(() => {
    if (token) return

    const timer = setTimeout(() => {
      setShowAuthModal(true)
    }, 3000)

    return () => clearTimeout(timer)
  }, [token])

  // Save to recent searches
  function addToRecent(query) {
    const updated = [query, ...recentSearches.filter((s) => s !== query)]
      .slice(0, MAX_RECENT)
    setRecentSearches(updated)
    localStorage.setItem(RECENT_KEY, JSON.stringify(updated))
  }

  // Auth handlers
  async function handleAuth() {
    if (!authEmail.trim() || !authPassword.trim()) return

    setAuthLoading(true)
    setAuthError("")

    const url = authMode === "login"
      ? "http://localhost:8000/api/login"
      : "http://localhost:8000/api/register"

    try {
      const response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: authEmail, password: authPassword })
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || "Authentication failed")
      }

      setToken(data.token)
      setUserEmail(data.email)
      localStorage.setItem(TOKEN_KEY, data.token)
      localStorage.setItem(EMAIL_KEY, data.email)
      setShowAuthModal(false)
    } catch (err) {
      setAuthError(err.message)
    } finally {
      setAuthLoading(false)
    }
  }

  function handleLogout() {
    setToken(null)
    setUserEmail("")
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(EMAIL_KEY)
    setSynthesis(null)
    setAuthEmail("")
    setAuthPassword("")
    setAuthError("")
    setShowAuthModal(true)
  }

  // Filtered autocomplete suggestions
  const filteredSuggestions = topic.length >= 2
    ? TOPICS.filter(
        (t) => t.includes(topic.toLowerCase()) && t !== topic.toLowerCase()
      ).slice(0, 5)
    : []

  // What shows in dropdown — recent or autocomplete
  const showRecent = topic.length < 2 && recentSearches.length > 0
  const dropdownItems = showRecent ? recentSearches : filteredSuggestions
  const dropdownVisible = showSuggestions && dropdownItems.length > 0

  // Reset selection when typing
  useEffect(() => {
    setSelectedIndex(-1)
  }, [topic])

  async function handleSearch(searchTopic) {
    const query = (searchTopic || topic).trim()
    if (query.length < 5) return

    // Token yoksa modal aç
    if (!token) {
      setShowAuthModal(true)
      return
    }

    setLoading(true)
    setSynthesis(null)
    setError("")
    setShowSuggestions(false)
    setSelectedIndex(-1)

    try {
      const response = await fetch("http://localhost:8000/api/search", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": "Bearer " + token
        },
        body: JSON.stringify({ topic: query })
      })

      if (response.status === 401) {
        handleLogout()
        return
      }

      if (!response.ok) {
        throw new Error("Server error: " + response.status)
      }

      const data = await response.json()
      setSynthesis(data.synthesis)
      addToRecent(query)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  function handleKeyDown(e) {
    if (!dropdownVisible) {
      if (e.key === "Enter") handleSearch()
      return
    }

    if (e.key === "ArrowDown") {
      e.preventDefault()
      setSelectedIndex((prev) =>
        prev < dropdownItems.length - 1 ? prev + 1 : 0
      )
    } else if (e.key === "ArrowUp") {
      e.preventDefault()
      setSelectedIndex((prev) =>
        prev > 0 ? prev - 1 : dropdownItems.length - 1
      )
    } else if (e.key === "Enter") {
      if (selectedIndex >= 0) {
        const selected = dropdownItems[selectedIndex]
        setTopic(selected)
        setShowSuggestions(false)
        handleSearch(selected)
      } else {
        handleSearch()
      }
    } else if (e.key === "Escape") {
      setShowSuggestions(false)
      setSelectedIndex(-1)
    }
  }

  function HighlightMatch({ text, query }) {
    if (!query || query.length < 2) return <span>{text}</span>

    const lower = text.toLowerCase()
    const idx = lower.indexOf(query.toLowerCase())
    if (idx === -1) return <span>{text}</span>

    return (
      <span>
        {text.slice(0, idx)}
        <strong className="text-blue-700">
          {text.slice(idx, idx + query.length)}
        </strong>
        {text.slice(idx + query.length)}
      </span>
    )
  }

  function SkeletonCard() {
    return (
      <div className="bg-white border border-gray-200 rounded-xl shadow-sm p-5
                      animate-pulse">
        <div className="flex items-center justify-between mb-3">
          <div className="h-7 bg-gray-200 rounded w-3/4"></div>
          <div className="h-6 bg-blue-100 rounded-full w-20"></div>
        </div>
        <div className="space-y-2">
          <div className="h-4 bg-gray-200 rounded w-full"></div>
          <div className="h-4 bg-gray-200 rounded w-full"></div>
          <div className="h-4 bg-gray-200 rounded w-5/6"></div>
        </div>
      </div>
    )
  }

  function SkeletonTheme() {
    return (
      <div className="bg-white border-l-4 border-l-gray-200 border border-gray-200
                      rounded-xl shadow-sm p-5 animate-pulse">
        <div className="h-5 bg-gray-200 rounded w-1/2 mb-3"></div>
        <div className="space-y-2 mb-4">
          <div className="h-4 bg-gray-200 rounded w-full"></div>
          <div className="h-4 bg-gray-200 rounded w-full"></div>
          <div className="h-4 bg-gray-200 rounded w-4/5"></div>
        </div>
        <div className="border-t border-gray-100 pt-3">
          <div className="h-3 bg-gray-100 rounded w-16 mb-2"></div>
          <div className="h-14 bg-gray-100 rounded w-full"></div>
        </div>
      </div>
    )
  }

  function PaperCard({ paperId, papers }) {
    const paper = papers[paperId]
    if (!paper) return null

    const year = paper.published ? paper.published.slice(0, 4) : ""
    const authors = paper.authors ? paper.authors.slice(0, 2).join(", ") : ""
    const source = paper.source || ""
    const isHighImpact = paper.citation_count && paper.citation_count > 1000

    const sourceColors = {
      arxiv: "bg-red-100 text-red-700",
      semantic_scholar: "bg-purple-100 text-purple-700",
      openalex: "bg-green-100 text-green-700"
    }

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
        <div className="flex flex-wrap items-center gap-2 mt-2 text-xs
                        text-gray-500">
          {authors && <span>{authors}</span>}
          {year && <span>· {year}</span>}
          {paper.citation_count != null && (
            <span className="bg-yellow-100 text-yellow-700 px-2 py-0.5
                             rounded-full font-medium">
              {paper.citation_count} citations
            </span>
          )}
          {source && (
            <span className={`px-2 py-0.5 rounded-full font-medium
              ${sourceColors[source] || "bg-gray-100 text-gray-600"}`}>
              {source}
            </span>
          )}
          {paper.paper_type && paper.paper_type !== "research" && (
            <span className="bg-indigo-100 text-indigo-700 px-2 py-0.5
                             rounded-full font-medium">
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
        <p className="text-xs font-semibold text-gray-400 uppercase
                      tracking-wide mb-2">
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

      {/* AUTH MODAL */}
      {showAuthModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/50 backdrop-blur-sm"></div>
          <div className="relative bg-white rounded-xl shadow-2xl p-8 w-full
                          max-w-sm mx-4">
            <h2 className="text-xl font-bold text-gray-800 text-center mb-1
                           font-heading">
              {authMode === "login" ? "Welcome Back" : "Create Account"}
            </h2>
            <p className="text-gray-500 text-sm text-center mb-5">
              Sign in to search and save your history
            </p>

            {authError && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-3
                              mb-4 text-red-700 text-sm text-center">
                {authError}
              </div>
            )}

            <input
              type="email"
              value={authEmail}
              onChange={(e) => setAuthEmail(e.target.value)}
              placeholder="Email"
              className="w-full border border-gray-300 rounded-lg px-4 py-2.5
                         mb-3 focus:outline-none focus:ring-2
                         focus:ring-blue-500 text-sm"
            />
            <input
              type="password"
              value={authPassword}
              onChange={(e) => setAuthPassword(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") handleAuth() }}
              placeholder="Password"
              className="w-full border border-gray-300 rounded-lg px-4 py-2.5
                         mb-4 focus:outline-none focus:ring-2
                         focus:ring-blue-500 text-sm"
            />
            <button
              onClick={handleAuth}
              disabled={authLoading}
              className="w-full bg-blue-600 text-white py-2.5 rounded-lg
                         font-medium hover:bg-blue-700 disabled:bg-blue-400
                         disabled:cursor-not-allowed text-sm"
            >
              {authLoading
                ? "Please wait..."
                : authMode === "login" ? "Sign In" : "Create Account"
              }
            </button>

            <p className="text-center text-xs text-gray-500 mt-4">
              {authMode === "login"
                ? "Don't have an account? "
                : "Already have an account? "
              }
              <button
                onClick={() => {
                  setAuthMode(authMode === "login" ? "register" : "login")
                  setAuthError("")
                }}
                className="text-blue-600 hover:underline font-medium"
              >
                {authMode === "login" ? "Sign Up" : "Sign In"}
              </button>
            </p>
          </div>
        </div>
      )}

      {/* HEADER */}
      <div className="bg-gradient-to-r from-blue-700 to-indigo-800
                      text-white py-10 px-4 text-center relative">
        {token && (
          <div className="absolute top-4 right-4 flex items-center gap-3">
            <span className="text-blue-200 text-sm">{userEmail}</span>
            <button
              onClick={handleLogout}
              className="text-sm bg-white/20 hover:bg-white/30 px-3 py-1
                         rounded-lg transition-colors"
            >
              Logout
            </button>
          </div>
        )}
        <h1 className="text-4xl font-bold tracking-tight font-heading">
          Academic Paper Assistant
        </h1>
        <p className="mt-2 text-blue-200 text-lg">
          Search, filter, and synthesize research papers with AI
        </p>
      </div>

      {/* MAIN CONTENT */}
      <div className="max-w-3xl mx-auto mt-10 px-4">
        <div className="flex gap-2 relative">
          <input
            type="text"
            value={topic}
            onChange={(e) => {
              setTopic(e.target.value)
              setShowSuggestions(true)
            }}
            onFocus={() => setShowSuggestions(true)}
            onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
            onKeyDown={handleKeyDown}
            placeholder="Enter a research topic..."
            className="flex-1 border border-gray-300 rounded-lg px-4 py-3
                       text-lg focus:outline-none focus:ring-2
                       focus:ring-blue-500 shadow-sm"
          />
          <button
            onClick={() => handleSearch()}
            disabled={loading || topic.trim().length < 5}
            className="bg-blue-600 text-white px-6 py-3 rounded-lg text-lg
                       font-medium hover:bg-blue-700
                       disabled:bg-blue-400 disabled:cursor-not-allowed
                       shadow-sm"
          >
            {loading ? "Searching..." : "Search"}
          </button>

          {dropdownVisible && (
            <div className="absolute left-0 right-16 top-full mt-1 bg-white
                            border border-gray-200 rounded-lg shadow-lg z-10
                            max-h-60 overflow-y-auto">
              {showRecent && (
                <p className="px-4 pt-2 pb-1 text-xs font-semibold
                              text-gray-400 uppercase tracking-wide">
                  Recent searches
                </p>
              )}
              {dropdownItems.map((item, i) => (
                <button
                  key={item}
                  onMouseDown={() => {
                    setTopic(item)
                    setShowSuggestions(false)
                    handleSearch(item)
                  }}
                  className={`w-full text-left px-4 py-2 text-sm
                    transition-colors
                    ${i === selectedIndex
                      ? "bg-blue-50 text-blue-700"
                      : "text-gray-700 hover:bg-gray-50"
                    }`}
                >
                  {showRecent ? (
                    <span className="flex items-center gap-2">
                      <span className="text-gray-400">🕐</span>
                      {item}
                    </span>
                  ) : (
                    <HighlightMatch text={item} query={topic} />
                  )}
                </button>
              ))}
            </div>
          )}
        </div>

        {topic.length > 0 && topic.trim().length < 5 && (
          <p className="mt-1 text-xs text-gray-400">
            Enter at least 5 characters to search
          </p>
        )}

        {!synthesis && !loading && (
          <div className="mt-3">
            <p className="text-xs text-gray-400 mb-2">Try a topic:</p>
            <div className="flex flex-wrap gap-2">
              {[
                "machine learning",
                "transformer architecture",
                "large language models",
                "computer vision",
                "reinforcement learning",
                "retrieval augmented generation"
              ].map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => {
                    setTopic(suggestion)
                    handleSearch(suggestion)
                  }}
                  className="text-sm bg-white border border-gray-200
                             rounded-full px-3 py-1 text-gray-600
                             hover:bg-blue-50 hover:border-blue-300
                             hover:text-blue-700 transition-all"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}

        {loading && (
          <div className="mt-8 space-y-6">
            <SkeletonCard />
            <SkeletonTheme />
            <SkeletonTheme />
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

            <div className="bg-white border border-gray-200 rounded-xl
                            shadow-sm p-5 border-t-4 border-t-indigo-500">
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
                                      border border-gray-200 rounded-xl
                                      shadow-sm p-5">
                <h3 className="text-lg font-semibold text-gray-800 mb-2
                               font-heading">
                  <span className="text-blue-500 mr-2">{i + 1}.</span>
                  {theme.title}
                </h3>
                <p className="text-gray-700 leading-7 text-justify
                              font-academic">
                  {theme.summary}
                </p>
                <SourceList paperIds={theme.paper_ids}
                            papers={synthesis.papers} />
              </div>
            ))}

            {synthesis.trends && synthesis.trends.length > 0 && (
              <div className="bg-white border-l-4 border-l-emerald-500
                              border border-gray-200 rounded-xl shadow-sm p-5">
                <h3 className="text-lg font-semibold text-gray-800 mb-3
                               font-heading">
                  📈 Research Trends
                </h3>
                {synthesis.trends.map((t, i) => (
                  <div key={i} className="mb-4 last:mb-0">
                    <p className="text-gray-700 leading-7 text-justify
                                  font-academic">
                      {t.trend}
                    </p>
                    <SourceList paperIds={t.paper_ids}
                                papers={synthesis.papers}
                                label="Related papers" />
                  </div>
                ))}
              </div>
            )}

            {synthesis.open_problems && synthesis.open_problems.length > 0 && (
              <div className="bg-white border-l-4 border-l-amber-500
                              border border-gray-200 rounded-xl shadow-sm p-5">
                <h3 className="text-lg font-semibold text-gray-800 mb-3
                               font-heading">
                  🔬 Open Problems
                </h3>
                {synthesis.open_problems.map((p, i) => (
                  <div key={i} className="mb-4 last:mb-0">
                    <p className="text-gray-700 leading-7 text-justify
                                  font-academic">
                      {p.problem}
                    </p>
                    <SourceList paperIds={p.paper_ids}
                                papers={synthesis.papers}
                                label="Relevant papers" />
                  </div>
                ))}
              </div>
            )}

            {synthesis.where_to_start && synthesis.where_to_start.length > 0 && (
              <div className="bg-blue-50 border-l-4 border-l-indigo-500
                              border border-blue-200 rounded-xl shadow-sm p-5">
                <h3 className="text-lg font-semibold text-blue-800 mb-3
                               font-heading">
                  📚 Where to Start
                </h3>
                <div className="space-y-3">
                  {synthesis.where_to_start.map((w, i) => (
                    <div key={i}>
                      <PaperCard paperId={w.paper_id}
                                 papers={synthesis.papers} />
                      <p className="text-sm text-gray-600 mt-1 ml-3
                                    font-academic">
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
        Academic Research Assistant · 2026
      </footer>
    </div>
  )
}

export default App
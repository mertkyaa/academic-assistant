import anthropic
from config import ANTHROPIC_API_KEY, ACTIVE_MODEL

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

ABBREVIATIONS = {
    "ml": "machine learning",
    "dl": "deep learning",
    "nlp": "natural language processing",
    "cv": "computer vision",
    "rl": "reinforcement learning",
    "llm": "large language models",
    "gan": "generative adversarial networks",
    "cnn": "convolutional neural network",
    "rnn": "recurrent neural network",
    "rag": "retrieval augmented generation",
    "ai": "artificial intelligence",
    "gpt": "generative pre-trained transformer",
    "bert": "bidirectional encoder representations from transformers",
    "svm": "support vector machine",
    "pca": "principal component analysis",
}


def expand_abbreviations(query):
    """Fast, deterministic expansion of well-known field abbreviations."""
    expanded = []
    for word in query.strip().split():
        expanded.append(ABBREVIATIONS.get(word.lower(), word))
    return " ".join(expanded)


NORMALIZE_SYSTEM = """You rewrite a user's research query into a concise ENGLISH \
academic search query for arXiv / OpenAlex / Semantic Scholar.

Rules:
- Translate non-English queries into English.
- Resolve proper nouns and place names to their precise, unambiguous meaning \
(e.g. "Alp Dağları" -> "European Alps mountain range", not the acronym "ALP").
- Spell out the intended sense of ambiguous acronyms; never leave a bare \
acronym that could match an unrelated field.
- Keep it short (2-8 words), just the core topic — no quotes, no explanation.

Output ONLY the rewritten query text, nothing else."""


def normalize_query(query):
    """Turn a raw (possibly non-English / ambiguous) query into a clean English
    academic search phrase. Falls back to abbreviation-expansion if the API call
    fails, so search still works."""
    base = expand_abbreviations(query)
    if not base:
        return base
    try:
        response = client.messages.create(
            model=ACTIVE_MODEL,
            max_tokens=40,
            system=NORMALIZE_SYSTEM,
            messages=[{"role": "user", "content": base}],
        )
        text = "".join(
            block.text for block in response.content if block.type == "text"
        ).strip().strip('"')
        print(f"Query normalize: {query!r} -> {text!r}")
        return text or base
    except Exception as e:
        print(f"Query normalize failed ({e}); using {base!r}")
        return base


# Backwards-compatible entry point used by the pipeline.
def preprocess_query(query):
    return normalize_query(query)


if __name__ == "__main__":
    print(preprocess_query("Alp Dağları"))
    print(preprocess_query("ML in NLP"))
    print(preprocess_query("derin öğrenme ile görüntü sınıflandırma"))

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


def preprocess_query(query):
    words = query.strip().split()
    expanded = []
    for word in words:
        lower = word.lower()
        if lower in ABBREVIATIONS:
            expanded.append(ABBREVIATIONS[lower])
        else:
            expanded.append(word)
    return " ".join(expanded)


if __name__ == "__main__":
    print(preprocess_query("ML in NLP"))
    print(preprocess_query("deep learning"))
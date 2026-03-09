"""TF-IDF lexical relevance score against seeded queries."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


def lexical_scores(
    chunk_texts: list[str],
    seeded_queries: list[str],
) -> list[float]:
    """Compute TF-IDF similarity of each chunk to the best-matching seeded query.

    Uses sklearn TfidfVectorizer and cosine similarity. Returns one score per chunk,
    normalized to 0..1 (max cosine with any query, clamped).
    """
    if not chunk_texts or not seeded_queries:
        return [0.0] * len(chunk_texts)

    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    corpus = list(chunk_texts) + list(seeded_queries)
    vectorizer = TfidfVectorizer(lowercase=True, max_features=5000)
    X = vectorizer.fit_transform(corpus)
    n_chunks = len(chunk_texts)
    chunk_vectors = X[:n_chunks]
    query_vectors = X[n_chunks:]

    # For each chunk, max cosine similarity to any query
    sim = cosine_similarity(chunk_vectors, query_vectors)
    # sim shape (n_chunks, n_queries); take max over queries
    max_sim = sim.max(axis=1)
    # Clamp to 0..1 (cosine is already in [-1,1], but TF-IDF usually non-negative)
    return [float(min(max(x, 0.0), 1.0)) for x in max_sim]

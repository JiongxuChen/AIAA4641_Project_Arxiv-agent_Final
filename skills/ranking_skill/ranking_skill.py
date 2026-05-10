"""Paper Ranking & Topic Structuring Skill.

This module ranks arXiv paper candidates by relevance to a user query and
assigns each paper to a lightweight topic cluster. It is designed to consume the
JSON output of the Paper Retrieval Skill and produce the input expected by the
Briefing Generation Skill.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
from collections import Counter
from collections.abc import Iterable
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "1")

from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


Paper = Dict[str, Any]

CORE_FIELDS = {
    "paper_id": "",
    "title": "",
    "authors": [],
    "abstract": "",
    "published": "",
    "categories": [],
    "pdf_url": "",
    "abs_url": "",
}

TOKEN_PATTERN = re.compile(r"[a-zA-Z][a-zA-Z0-9_+\-.]*")
EXTRA_STOP_WORDS = {
    "paper",
    "study",
    "studies",
    "approach",
    "method",
    "methods",
    "model",
    "models",
    "using",
    "based",
    "new",
    "show",
    "shows",
    "propose",
    "proposes",
    "proposed",
}
STOP_WORDS = set(ENGLISH_STOP_WORDS).union(EXTRA_STOP_WORDS)


def rank_and_cluster(
    query: str,
    papers: Sequence[Paper],
    top_n: Optional[int] = None,
    min_clusters: int = 2,
    max_clusters: int = 4,
) -> List[Paper]:
    """Rank papers by query relevance and assign each paper a topic cluster.

    Args:
        query: User research topic, e.g. "llm agents".
        papers: Candidate papers from the retrieval skill.
        top_n: Optional number of highest ranked papers to return. By default,
            all papers are returned, which matches the team interface standard.
        min_clusters: Minimum number of clusters when there are enough papers.
        max_clusters: Maximum number of clusters.

    Returns:
        A list of paper dictionaries sorted by descending relevance_score. Each
        paper includes relevance_score, rank, and cluster fields.
    """

    query = _normalize_query(query)
    if not papers:
        return []

    normalized_papers = [_normalize_paper(paper, index) for index, paper in enumerate(papers)]
    _validate_unique_paper_ids(normalized_papers)
    documents = [_paper_text(paper) for paper in normalized_papers]

    tfidf_scores, _, _ = _tfidf_relevance(query, documents)
    keyword_scores = [_keyword_relevance(query, paper) for paper in normalized_papers]

    scored_papers: List[Paper] = []
    for paper, tfidf_score, keyword_score in zip(normalized_papers, tfidf_scores, keyword_scores):
        score = (0.7 * tfidf_score) + (0.3 * keyword_score)
        item = dict(paper)
        item["relevance_score"] = round(float(max(0.0, min(1.0, score))), 4)
        scored_papers.append(item)

    scored_papers.sort(
        key=lambda item: (
            -item["relevance_score"],
            item.get("published", ""),
            item.get("paper_id", ""),
            item.get("title", ""),
        )
    )

    cluster_labels = _cluster_papers(
        query=query,
        ranked_papers=scored_papers,
        min_clusters=min_clusters,
        max_clusters=max_clusters,
    )

    for rank, paper in enumerate(scored_papers, start=1):
        paper["rank"] = rank
        paper["cluster"] = cluster_labels[paper["paper_id"]]

    if top_n is not None:
        if top_n < 0:
            raise ValueError("top_n must be non-negative")
        scored_papers = scored_papers[:top_n]
        for rank, paper in enumerate(scored_papers, start=1):
            paper["rank"] = rank

    return scored_papers


def save_ranking_visualization(
    ranked_papers: Sequence[Paper],
    output_path: str | Path = "ranking_visualization.png",
    query: str = "",
    max_nodes: int = 12,
) -> Path:
    """Create a PNG similarity network for ranked papers.

    Nodes are papers, node size reflects relevance score, node color reflects
    cluster, and edges connect semantically similar papers. The figure is useful
    for the visualization requirement in the individual report.
    """

    if not ranked_papers:
        raise ValueError("ranked_papers must contain at least one paper")

    import matplotlib.pyplot as plt
    import networkx as nx

    papers = list(ranked_papers)[:max_nodes]
    documents = [_paper_text(_normalize_paper(paper, index)) for index, paper in enumerate(papers)]
    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), min_df=1)
    matrix = vectorizer.fit_transform(documents)
    similarities = cosine_similarity(matrix)

    graph = nx.Graph()
    for paper in papers:
        graph.add_node(
            paper["paper_id"],
            label=f"#{paper.get('rank', '?')}",
            title=paper.get("title", ""),
            cluster=paper.get("cluster", "unclustered"),
            score=float(paper.get("relevance_score", 0.0)),
        )

    _add_similarity_edges(graph, papers, similarities)

    clusters = sorted({paper.get("cluster", "unclustered") for paper in papers})
    color_map = {
        cluster: color
        for cluster, color in zip(
            clusters,
            [
                "#2563eb",
                "#16a34a",
                "#dc2626",
                "#9333ea",
                "#ea580c",
                "#0891b2",
                "#4f46e5",
                "#65a30d",
            ],
        )
    }

    node_colors = [color_map[graph.nodes[node]["cluster"]] for node in graph.nodes]
    node_sizes = [450 + 2200 * graph.nodes[node]["score"] for node in graph.nodes]
    edge_widths = [0.8 + 3.0 * graph.edges[edge]["weight"] for edge in graph.edges]
    edge_colors = [graph.edges[edge]["weight"] for edge in graph.edges]

    fig, ax = plt.subplots(figsize=(11, 7), dpi=150)
    pos = nx.spring_layout(graph, seed=42, weight="weight", k=0.75)
    nx.draw_networkx_nodes(
        graph,
        pos,
        node_color=node_colors,
        node_size=node_sizes,
        linewidths=1.4,
        edgecolors="white",
        ax=ax,
    )
    nx.draw_networkx_edges(
        graph,
        pos,
        width=edge_widths,
        edge_color=edge_colors,
        edge_cmap=plt.cm.Greys,
        alpha=0.55,
        ax=ax,
    )
    nx.draw_networkx_labels(
        graph,
        pos,
        labels={node: graph.nodes[node]["label"] for node in graph.nodes},
        font_color="white",
        font_weight="bold",
        font_size=9,
        ax=ax,
    )

    legend_handles = [
        plt.Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            label=cluster,
            markerfacecolor=color_map[cluster],
            markersize=9,
        )
        for cluster in clusters
    ]
    ax.legend(handles=legend_handles, loc="lower left", frameon=False, fontsize=8)
    title = "Paper Similarity Network"
    if query:
        title += f": {query}"
    ax.set_title(title, fontsize=14, pad=12)
    ax.text(
        0.99,
        0.01,
        "Node size = relevance; edge weight = TF-IDF similarity",
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=8,
        color="#525252",
    )
    ax.axis("off")
    fig.tight_layout()

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, bbox_inches="tight")
    plt.close(fig)
    return output


def load_ranking_input(path: str | Path) -> Tuple[str, List[Paper]]:
    """Load either {"query": ..., "papers": [...]} or a raw paper list."""

    with Path(path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if isinstance(data, dict):
        query = data.get("query", "")
        papers = data.get("papers", [])
    elif isinstance(data, list):
        query = ""
        papers = data
    else:
        raise ValueError("Input JSON must be a dict with query/papers or a paper list")
    return query, papers


def _normalize_query(query: str) -> str:
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string")
    return " ".join(query.strip().split())


def _normalize_paper(paper: Paper, index: int) -> Paper:
    if not isinstance(paper, dict):
        raise ValueError(f"paper at index {index} must be a dictionary")

    normalized = dict(CORE_FIELDS)
    normalized.update(paper)
    normalized["paper_id"] = str(normalized.get("paper_id") or f"paper_{index + 1}")
    normalized["title"] = str(normalized.get("title") or "")
    normalized["abstract"] = str(normalized.get("abstract") or "")
    normalized["published"] = str(normalized.get("published") or "")

    authors = normalized.get("authors", [])
    if isinstance(authors, str):
        authors = [authors]
    normalized["authors"] = list(authors) if isinstance(authors, Iterable) else []

    categories = normalized.get("categories", [])
    if isinstance(categories, str):
        categories = [categories]
    normalized["categories"] = list(categories) if isinstance(categories, Iterable) else []

    normalized["pdf_url"] = str(normalized.get("pdf_url") or "")
    normalized["abs_url"] = str(normalized.get("abs_url") or "")
    return normalized


def _validate_unique_paper_ids(papers: Sequence[Paper]) -> None:
    seen_ids = set()
    for paper in papers:
        paper_id = paper["paper_id"]
        if paper_id in seen_ids:
            raise ValueError(f"duplicate paper_id found: {paper_id}")
        seen_ids.add(paper_id)


def _paper_text(paper: Paper) -> str:
    title = paper.get("title", "")
    abstract = paper.get("abstract", "")
    categories = " ".join(paper.get("categories", []))
    return f"{title} {title} {title} {abstract} {categories}"


def _tfidf_relevance(
    query: str, documents: Sequence[str]
) -> Tuple[List[float], Any, TfidfVectorizer]:
    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), min_df=1)
    try:
        matrix = vectorizer.fit_transform([query, *documents])
    except ValueError:
        return [0.0 for _ in documents], None, vectorizer
    similarities = cosine_similarity(matrix[0], matrix[1:]).flatten()
    return [float(score) for score in similarities], matrix[1:], vectorizer


def _keyword_relevance(query: str, paper: Paper) -> float:
    query_tokens = _tokens(query)
    if not query_tokens:
        return 0.0

    title_tokens = Counter(_tokens(paper.get("title", "")))
    abstract_tokens = Counter(_tokens(paper.get("abstract", "")))
    category_text = " ".join(paper.get("categories", []))
    category_tokens = Counter(_tokens(category_text))

    weighted_hits = 0.0
    matched_terms = set()
    for token in query_tokens:
        token_hits = (
            2.5 * title_tokens[token]
            + 1.0 * abstract_tokens[token]
            + 1.5 * category_tokens[token]
        )
        weighted_hits += token_hits
        if token_hits > 0:
            matched_terms.add(token)

    coverage = len(matched_terms) / len(set(query_tokens))
    saturation = 1.0 - math.exp(-weighted_hits / max(1.0, len(query_tokens) * 2.0))
    return float(0.55 * saturation + 0.45 * coverage)


def _cluster_papers(
    query: str,
    ranked_papers: Sequence[Paper],
    min_clusters: int,
    max_clusters: int,
) -> Dict[str, str]:
    paper_count = len(ranked_papers)
    if paper_count == 1:
        return {ranked_papers[0]["paper_id"]: _document_label(ranked_papers[0], query)}

    cluster_count = _choose_cluster_count(paper_count, min_clusters, max_clusters)
    documents = [_paper_text(paper) for paper in ranked_papers]
    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), min_df=1)

    try:
        matrix = vectorizer.fit_transform(documents)
        model = KMeans(n_clusters=cluster_count, random_state=42, n_init=10)
        raw_labels = model.fit_predict(matrix)
        label_names = _name_clusters(model.cluster_centers_, vectorizer, query)
    except Exception:
        raw_labels = np.array([index % cluster_count for index in range(paper_count)])
        label_names = {index: f"topic {index + 1}" for index in range(cluster_count)}

    assignments: Dict[str, str] = {}
    for paper, label_id in zip(ranked_papers, raw_labels):
        assignments[paper["paper_id"]] = label_names.get(int(label_id), f"topic {int(label_id) + 1}")

    if paper_count >= 2 and len(set(assignments.values())) < 2:
        assignments = _fallback_split_labels(ranked_papers, query)

    return assignments


def _choose_cluster_count(paper_count: int, min_clusters: int, max_clusters: int) -> int:
    if min_clusters < 1 or max_clusters < 1:
        raise ValueError("min_clusters and max_clusters must be positive")
    if min_clusters > max_clusters:
        raise ValueError("min_clusters cannot be greater than max_clusters")
    suggested = max(min_clusters, int(round(math.sqrt(paper_count))))
    return max(1, min(paper_count, max_clusters, suggested))


def _name_clusters(
    centers: np.ndarray, vectorizer: TfidfVectorizer, query: str, terms_per_label: int = 3
) -> Dict[int, str]:
    features = np.array(vectorizer.get_feature_names_out())
    query_terms = set(_tokens(query))
    labels: Dict[int, str] = {}
    used_labels = set()

    for cluster_id, center in enumerate(centers):
        order = np.argsort(center)[::-1]
        terms = []
        for feature_index in order:
            term = features[feature_index]
            term_tokens = _tokens(term)
            if not term_tokens:
                continue
            if all(token in STOP_WORDS for token in term_tokens):
                continue
            if set(term_tokens).issubset(query_terms) and len(terms) < terms_per_label - 1:
                continue
            terms.append(term)
            if len(terms) == terms_per_label:
                break

        if not terms:
            terms = [f"topic {cluster_id + 1}"]

        label = _clean_label(" ".join(terms[:terms_per_label]))
        if label in used_labels:
            label = f"{label} {cluster_id + 1}"
        labels[cluster_id] = label
        used_labels.add(label)

    return labels


def _fallback_split_labels(ranked_papers: Sequence[Paper], query: str) -> Dict[str, str]:
    midpoint = max(1, len(ranked_papers) // 2)
    assignments: Dict[str, str] = {}
    for index, paper in enumerate(ranked_papers):
        if index < midpoint:
            label = _document_label(paper, query) or "primary topic"
        else:
            label = _document_label(paper, query) or "secondary topic"
            if label == assignments.get(ranked_papers[0]["paper_id"]):
                label = "secondary topic"
        assignments[paper["paper_id"]] = label
    return assignments


def _document_label(paper: Paper, query: str) -> str:
    query_terms = set(_tokens(query))
    text_tokens = [
        token
        for token in _tokens(f"{paper.get('title', '')} {paper.get('abstract', '')}")
        if token not in STOP_WORDS and token not in query_terms
    ]
    common = [token for token, _ in Counter(text_tokens).most_common(3)]
    if common:
        return _clean_label(" ".join(common))
    categories = paper.get("categories", [])
    if categories:
        return str(categories[0])
    return "general research"


def _add_similarity_edges(graph: Any, papers: Sequence[Paper], similarities: np.ndarray) -> None:
    threshold = 0.18
    for i, paper_i in enumerate(papers):
        candidates: List[Tuple[float, int]] = []
        for j, paper_j in enumerate(papers):
            if i >= j:
                continue
            similarity = float(similarities[i, j])
            if similarity >= threshold:
                graph.add_edge(paper_i["paper_id"], paper_j["paper_id"], weight=similarity)
            candidates.append((similarity, j))

        if not any(edge for edge in graph.edges(paper_i["paper_id"])) and candidates:
            best_similarity, best_index = max(candidates, key=lambda item: item[0])
            if best_similarity > 0:
                graph.add_edge(
                    paper_i["paper_id"],
                    papers[best_index]["paper_id"],
                    weight=best_similarity,
                )


def _tokens(text: str) -> List[str]:
    return [match.group(0).lower() for match in TOKEN_PATTERN.finditer(text or "")]


def _clean_label(label: str) -> str:
    label = re.sub(r"\s+", " ", label.strip().lower())
    words = []
    for word in label.split():
        if word not in words:
            words.append(word)
    return " ".join(words[:5]) or "general research"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rank and cluster arXiv paper candidates.")
    parser.add_argument("--input", required=True, help="JSON file with query and papers")
    parser.add_argument("--query", default=None, help="Override query from input JSON")
    parser.add_argument("--output", default="sample_output_ranking.json", help="Output JSON path")
    parser.add_argument("--top-n", type=int, default=None, help="Return only top N papers")
    parser.add_argument(
        "--visualize",
        default=None,
        help="Optional PNG path for the paper similarity network visualization",
    )
    parser.add_argument("--min-clusters", type=int, default=2, help="Minimum number of clusters")
    parser.add_argument("--max-clusters", type=int, default=4, help="Maximum number of clusters")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    input_query, papers = load_ranking_input(args.input)
    query = args.query if args.query is not None else input_query
    ranked = rank_and_cluster(
        query=query,
        papers=papers,
        top_n=args.top_n,
        min_clusters=args.min_clusters,
        max_clusters=args.max_clusters
    )

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with Path(args.output).open("w", encoding="utf-8") as handle:
        json.dump(ranked, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    print(f"Ranking saved to: {args.output}")

    if args.visualize:
        save_ranking_visualization(ranked, output_path=args.visualize, query=query)
        print(f"Visualization saved to: {args.visualize}")


if __name__ == "__main__":
    main()
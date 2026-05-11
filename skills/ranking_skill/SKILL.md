# arXiv Ranking Skill

## Name

arxiv-ranking-skill

## Description

Rank and cluster retrieved arXiv papers according to their relevance to a user
research query.

## Functionality

The skill represents papers with text features from titles and abstracts,
computes relevance scores against the query, ranks papers, and groups them into
clusters for easier briefing generation and review.

## Inputs

- `query`: user research topic.
- `papers`: list of normalized paper dictionaries.
- `top_n`: number of ranked papers to keep.
- `min_clusters`: minimum number of clusters.
- `max_clusters`: maximum number of clusters.

## Outputs

A ranked list of paper dictionaries enriched with relevance and cluster
information.

## Main File

- `ranking_skill.py`

## Main API

```python
from ranking_skill import rank_and_cluster

ranked = rank_and_cluster(
    query="LLM agents",
    papers=papers,
    top_n=10,
)
```

## Agent Integration

The agent calls this skill after retrieval and before briefing generation. The
ranked output is saved into `briefings/ranking_*.json`.

For detailed documentation, see `README.md` in this skill folder.

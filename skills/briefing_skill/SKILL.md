# arXiv Briefing Skill

## Name

arxiv-briefing-skill

## Description

Generate a structured Markdown research briefing from ranked arXiv papers.

## Functionality

The skill turns ranked papers into a readable research briefing with a summary
table, key paper highlights, and concise descriptions of relevance to the user
query. It can optionally use an LLM for enhanced briefing content.

## Inputs

- `query`: user research topic.
- `papers`: ranked paper dictionaries.
- `top_k`: number of papers to include.
- `use_llm`: whether to use LLM-enhanced generation.
- `model`: optional LLM model name.

## Outputs

A Markdown briefing string, usually saved as `briefings/briefing_*.md`.

## Main File

- `briefing_skill.py`

## Main API

```python
from briefing_skill import generate_briefing, save_briefing

briefing = generate_briefing(
    query="LLM agents",
    papers=ranked_papers,
    top_k=10,
)
save_briefing(briefing, "briefing.md")
```

## Agent Integration

The agent calls this skill at the end of the full pipeline. Generated briefings
are displayed in the Web UI task detail view and saved under `briefings/`.

For detailed documentation, see `README.md` in this skill folder.

# arXiv Retrieval Skill

## Name

arxiv-retrieval-skill

## Description

Retrieve recent candidate papers from the arXiv API based on a user research
query. The skill supports single keywords, single phrases, and comma-separated
multi-term queries such as `LLM, Deep learning`.

## Functionality

The skill converts a user query into an arXiv search expression, fetches papers
through the arXiv API, parses the Atom XML response, normalizes papers into the
project's dictionary schema, deduplicates results, filters by publication date,
and optionally saves results as JSON or CSV.

## Inputs

- `query`: a keyword, phrase, or comma-separated list of keywords/phrases.
- `days`: recent-day window for filtering papers.
- `max_results`: maximum number of papers to return.
- `output`: optional output file path.
- `format`: optional output format, either `json` or `csv`.

## Outputs

A list of paper dictionaries. Each paper contains:

- `paper_id`
- `title`
- `authors`
- `abstract`
- `published`
- `categories`
- `pdf_url`
- `abs_url`

## Main File

- `retrieval_skill.py`

## Main API

```python
from retrieval_skill import retrieve_papers

papers = retrieve_papers(
    query="LLM, Deep learning",
    days=7,
    max_results=20,
)
```

## CLI Example

```bash
python retrieval_skill.py --query "LLM, Deep learning" --days 7 --max-results 20 --output papers.json
```

## Agent Integration

The agent calls this skill before ranking and briefing. Retrieval results are
saved into `briefings/retrieval_*.json`, optionally added to
`papers_library.json`, and recorded in `task_history.json`.

For detailed documentation, see `README.md` in this skill folder.

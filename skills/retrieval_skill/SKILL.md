# arXiv Retrieval Skill

## Name

arxiv-retrieval-skill

## Description

Retrieve recent candidate papers from arXiv for a user-provided research query. The skill supports single keywords, single phrases, and comma-separated multi-term alternatives such as `LLM, Deep learning`. It returns normalized paper dictionaries that can be consumed by the agent's ranking, briefing, paper-library, and follow-up query components.

## Functionality

The skill performs the retrieval stage of the research briefing workflow:

1. Parse and normalize the user query.
2. Convert terms into an arXiv `search_query`.
3. Add a recent-day `submittedDate` range when `days > 0`.
4. Fetch arXiv Atom XML through the export API with bounded retries and pagination.
5. Parse titles, authors, abstracts, dates, categories, and links.
6. Normalize arXiv identifiers by removing version suffixes.
7. Deduplicate papers by `paper_id`.
8. Return only the eight core fields used by the rest of the agent.

If arXiv returns HTTP 429, the skill falls back to searching the local project `papers_library.json`. This fallback is not a cache and does not create new files.

## Inputs

Programmatic API:

- `query`: non-empty keyword, phrase, or comma-separated list of keywords/phrases.
- `days`: non-negative recent-day window. `0` disables date filtering.
- `max_results`: positive maximum number of papers to return, capped at 200.

CLI-only options:

- `output`: output file path.
- `format`: output format, either `json` or `csv`.
- `check_existing`: skip papers already present in a library after retrieval.
- `force`: save retrieved papers even when duplicates are found.
- `library_path`: library path used by the duplicate check.

## Outputs

A list of paper dictionaries. Each returned paper contains exactly:

- `paper_id`
- `title`
- `authors`
- `abstract`
- `published`
- `categories`
- `pdf_url`
- `abs_url`

Example:

```json
{
  "paper_id": "arxiv_2501.12345",
  "title": "Example Paper Title",
  "authors": ["Author A", "Author B"],
  "abstract": "This paper studies ...",
  "published": "2026-04-01",
  "categories": ["cs.LG", "cs.AI"],
  "pdf_url": "https://arxiv.org/pdf/2501.12345.pdf",
  "abs_url": "https://arxiv.org/abs/2501.12345"
}
```

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

Optional duplicate filtering:

```bash
python retrieval_skill.py --query "LLM agents" --check-existing --library-path ../../papers_library.json
```

## Query Examples

| Input | Interpretation |
|-------|----------------|
| `LLM` | Single keyword. |
| `Deep learning` | Single phrase. |
| `LLM, Deep learning` | Alternative terms combined with `OR`. |

## Agent Integration

The agent calls this skill before ranking and briefing. Retrieval results may be saved into `briefings/retrieval_*.json`, added to `papers_library.json`, recorded in `task_history.json`, and reused as context for follow-up conversations.

For detailed documentation, see `README.md` in this skill folder.
